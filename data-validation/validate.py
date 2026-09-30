"""Validate a Rhombus AI pipeline output against the cleaning rules.

Usage:
    python validate.py --scenario baseline \
        --input s3://rhombus-qa-source-shwan/input/orders.csv \
        --output gs://rhombus-qa-dest-shwan/<output path> \
        [--expected-rows 28] [--compare-with <previous output>] [--baseline <reference file>]
        [--expect-identical]

--input / --output / --compare-with / --baseline accept a local path, s3://bucket/key
or gs://bucket/key. A gs:// URI ending in "/" is treated as a prefix and the most
recently updated object under it is used.

--baseline is the reference for the order_date semantic check (raw baseline input or a
cleaned baseline output); it defaults to --input. --expect-identical adds a pass-through
identity check: every output cell must equal the input cell at the same position.

Writes results/<scenario>-<timestamp>.json and exits 1 if any check fails.
"""
import argparse
import hashlib
import io
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

import rules

HERE = Path(__file__).resolve().parent
RESULTS_DIR = HERE / "results"
load_dotenv(HERE.parent / ".env")

# Column order of datasets/baseline_orders.csv, which the cleaned output must keep.
EXPECTED_COLUMNS = [
    "order_id",
    "customer_name",
    "email",
    "phone",
    "state",
    "order_date",
    "amount_usd",
    "quantity",
    "status",
]


# --- Loading -------------------------------------------------------------------
def _read_bytes(location: str) -> tuple[bytes, str]:
    """Return (content, resolved location) for a local path, s3:// or gs:// URI."""
    if location.startswith("s3://"):
        import boto3

        bucket, _, key = location[5:].partition("/")
        session = boto3.Session(profile_name=os.getenv("AWS_PROFILE") or None,
                                region_name=os.getenv("AWS_REGION") or None)
        obj = session.client("s3").get_object(Bucket=bucket, Key=key)
        return obj["Body"].read(), location

    if location.startswith("gs://"):
        from google.cloud import storage

        bucket_name, _, name = location[5:].partition("/")
        bucket = storage.Client().bucket(bucket_name)
        if name == "" or name.endswith("/"):
            blobs = [b for b in bucket.list_blobs(prefix=name) if not b.name.endswith("/")]
            if not blobs:
                raise FileNotFoundError(f"no objects under {location}")
            blob = max(blobs, key=lambda b: b.updated)
        else:
            blob = bucket.blob(name)
        return blob.download_as_bytes(), f"gs://{bucket_name}/{blob.name}"

    return Path(location).read_bytes(), str(Path(location).resolve())


def load_csv(location: str) -> tuple[pd.DataFrame, str]:
    content, resolved = _read_bytes(location)
    # Read everything as text so formatting (e.g. "12.50", leading zeros) is preserved.
    df = pd.read_csv(io.BytesIO(content), dtype=str, keep_default_na=False)
    return df, resolved


# --- Checks --------------------------------------------------------------------
def check_schema(df: pd.DataFrame):
    actual = list(df.columns)
    if actual == EXPECTED_COLUMNS:
        return rules.CheckResult(True, "columns and order match")
    missing = [c for c in EXPECTED_COLUMNS if c not in actual]
    extra = [c for c in actual if c not in EXPECTED_COLUMNS]
    parts = []
    if missing:
        parts.append(f"missing {missing}")
    if extra:
        parts.append(f"unexpected {extra}")
    if not parts:
        parts.append(f"order differs: {actual}")
    return rules.CheckResult(False, "; ".join(parts))


def check_row_count(df: pd.DataFrame, expected: int | None):
    if expected is None:
        return rules.CheckResult(True, f"SKIPPED: {len(df)} rows (no --expected-rows given)")
    return rules.CheckResult(len(df) == expected, f"{len(df)} rows, expected {expected}")


def normalise(df: pd.DataFrame) -> pd.DataFrame:
    """Order-independent form used for hashing and diffing."""
    out = df.copy()
    out = out[sorted(out.columns)]
    for col in out.columns:
        out[col] = out[col].str.strip()
    return out.sort_values(list(out.columns)).reset_index(drop=True)


def sha256_of(df: pd.DataFrame) -> str:
    return hashlib.sha256(normalise(df).to_csv(index=False, lineterminator="\n").encode()).hexdigest()


def check_determinism(df: pd.DataFrame, previous: pd.DataFrame | None):
    current_hash = sha256_of(df)
    if previous is None:
        return rules.CheckResult(True, f"SKIPPED: sha256={current_hash} (no --compare-with given)")
    previous_hash = sha256_of(previous)
    if current_hash == previous_hash:
        return rules.CheckResult(True, f"identical output (sha256={current_hash})")

    a, b = normalise(df), normalise(previous)
    if list(a.columns) != list(b.columns):
        return rules.CheckResult(False, f"hash differs; columns differ: {list(a.columns)} vs {list(b.columns)}")
    rows_a = set(map(tuple, a.itertuples(index=False)))
    rows_b = set(map(tuple, b.itertuples(index=False)))
    only_new = sorted(rows_a - rows_b)[: rules.MAX_EXAMPLES]
    only_old = sorted(rows_b - rows_a)[: rules.MAX_EXAMPLES]
    return rules.CheckResult(False, (
        f"hash differs ({current_hash[:12]} vs {previous_hash[:12]}); "
        f"{len(rows_a - rows_b)} row(s) only in current, {len(rows_b - rows_a)} only in previous; "
        f"current-only e.g. {only_new}; previous-only e.g. {only_old}"
    ))


# --- Reporting -----------------------------------------------------------------
def print_table(results: list[dict]):
    width = max(len(r["check"]) for r in results)
    print(f"\n{'CHECK'.ljust(width)}  RESULT  ROWS  DETAILS")
    print(f"{'-' * width}  ------  ----  {'-' * 50}")
    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        rows = "-" if r["violations"] is None else str(r["violations"])
        line = f"{r['check'].ljust(width)}  {status:<6}  {rows:>4}  {r['details']}"
        if r["examples"]:
            line += f"\n{' ' * (width + 16)}e.g. {', '.join(r['examples'])}"
        print(line)
    failed = sum(not r["passed"] for r in results)
    print(f"\n{len(results) - failed} passed, {failed} failed\n")


def print_identity_columns(per_column: dict):
    width = max(len(c) for c in per_column)
    print(f"{'COLUMN'.ljust(width)}  CHANGED  EXAMPLE")
    print(f"{'-' * width}  -------  {'-' * 40}")
    for col, info in per_column.items():
        print(f"{col.ljust(width)}  {info['changed']:>7}  {info['example']}")
    print()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scenario", required=True, help="name used in the report file, e.g. baseline, schema-drop-column")
    parser.add_argument("--input", required=True, help="source CSV fed to the pipeline (local, s3:// or gs://)")
    parser.add_argument("--output", required=True, help="pipeline output CSV (local, s3:// or gs://)")
    parser.add_argument("--expected-rows", type=int, help="expected number of rows in the output")
    parser.add_argument("--compare-with", help="previous output to check determinism against")
    parser.add_argument("--baseline", help="reference file for the order_date semantic check (default: --input)")
    parser.add_argument("--expect-identical", action="store_true",
                        help="pass-through run: every output cell must equal the input")
    args = parser.parse_args(argv)

    input_df, input_src = load_csv(args.input)
    output_df, output_src = load_csv(args.output)
    previous_df = load_csv(args.compare_with)[0] if args.compare_with else None
    reference_df = load_csv(args.baseline)[0] if args.baseline else input_df

    checks = [
        ("schema", "schema", lambda: check_schema(output_df)),
        ("row_count", "row count", lambda: check_row_count(output_df, args.expected_rows)),
        *[("cleaning", name, (lambda f=fn: f(output_df))) for name, fn in rules.CLEANING_RULES],
        ("semantic", "S01 amount_usd in 5-500 range", lambda: rules.check_amount_in_baseline_range(output_df)),
        ("semantic", "S02 order_date same day as reference", lambda: rules.check_dates_match_reference(output_df, reference_df)),
        ("platform", "P01 order_id stays integer", lambda: rules.check_order_id_integer_strings(output_df)),
        ("platform", "P02 no silent nulling", lambda: rules.check_no_silent_nulling(output_df, input_df)),
        ("determinism", "determinism (sha256)", lambda: check_determinism(output_df, previous_df)),
    ]
    if args.expect_identical:
        checks.append(("identity", "I01 output identical to input", lambda: rules.check_identical(output_df, input_df)))

    results = []
    for category, name, run in checks:
        try:
            r = run()
        except Exception as exc:  # a crashing check is a failed check, not a crashed report
            r = rules.CheckResult(False, f"ERROR: {type(exc).__name__}: {exc}")
        results.append({"category": category, "check": name, "passed": bool(r.passed), "details": r.details,
                        "violations": r.violations, "examples": r.examples, **r.extra})

    print(f"Scenario: {args.scenario}")
    print(f"Input:    {input_src} ({len(input_df)} rows, columns={list(input_df.columns)})")
    print(f"Output:   {output_src} ({len(output_df)} rows)")
    print_table(results)
    for r in results:
        if "per_column" in r:
            print("Changed cells per column (output vs input, same row position):")
            print_identity_columns(r["per_column"])

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    RESULTS_DIR.mkdir(exist_ok=True)
    report_path = RESULTS_DIR / f"{args.scenario}-{timestamp}.json"
    report = {
        "scenario": args.scenario,
        "timestamp": timestamp,
        "input": {"location": input_src, "rows": len(input_df), "columns": list(input_df.columns)},
        "output": {"location": output_src, "rows": len(output_df), "columns": list(output_df.columns),
                   "sha256": sha256_of(output_df)},
        "compare_with": args.compare_with,
        "baseline": args.baseline or args.input,
        "expect_identical": args.expect_identical,
        "passed": all(r["passed"] for r in results),
        "results": results,
    }
    report_path.write_text(json.dumps(report, indent=2))
    print(f"Report written to {report_path.relative_to(HERE)}")

    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
