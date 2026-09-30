"""Cleaning rules and semantic checks for the orders dataset.

Every check takes DataFrames whose values were all read as strings and returns a
CheckResult: passed / details, plus the number of violating rows and up to
MAX_EXAMPLES example order_ids. Checks are small and independent so each failure
points at exactly one rule.
"""
import re
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

# --- Thresholds / reference values ---------------------------------------------
VALID_STATES = {"NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"}
VALID_STATUSES = {"pending", "shipped", "delivered", "cancelled"}
PHONE_PATTERN = r"^04\d{8}$"
EMAIL_PATTERN = r"^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$"
DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"
AMOUNT_PATTERN = r"^\d+\.\d{2}$"
ORDER_ID_PATTERN = r"^\d+$"
AMOUNT_MIN = 5.00   # baseline range (semantic check)
AMOUNT_MAX = 500.00
MAX_EXAMPLES = 5    # how many offending order_ids to show


@dataclass
class CheckResult:
    passed: bool
    details: str
    violations: int | None = None          # rows (or cells) that broke the check; None = not row-based
    examples: list = field(default_factory=list)
    extra: dict = field(default_factory=dict)


# --- Helpers ---------------------------------------------------------------------
def _label(df: pd.DataFrame, idx) -> str:
    """order_id of a row, or its CSV line number when the order_id is blank."""
    order_id = df.at[idx, "order_id"] if "order_id" in df.columns else ""
    return order_id if order_id.strip() else f"<blank order_id, line {idx + 2}>"


def _missing(df: pd.DataFrame, *cols: str) -> CheckResult | None:
    absent = [c for c in cols if c not in df.columns]
    return CheckResult(False, f"column(s) missing: {absent}") if absent else None


def _from_mask(df: pd.DataFrame, bad: pd.Series, what: str) -> CheckResult:
    n = int(bad.sum())
    if not n:
        return CheckResult(True, f"all {len(df)} rows OK", 0)
    examples = list(dict.fromkeys(_label(df, i) for i in df.index[bad]))[:MAX_EXAMPLES]
    return CheckResult(False, f"{n} row(s) {what}", n, examples)


def id_key(order_id: str) -> str:
    """Join key for matching rows across files. '1001.0' -> '1001', so rows can still
    be matched when the platform turned the integer id into a float."""
    value = order_id.strip()
    return re.sub(r"^(\d+)\.0+$", r"\1", value)


def parse_date(value: str) -> str | None:
    """ISO date for a YYYY-MM-DD or MM/DD/YYYY string, or None if it isn't a real date."""
    value = value.strip()
    for pattern, fmt in ((r"\d{4}-\d{2}-\d{2}", "%Y-%m-%d"), (r"\d{2}/\d{2}/\d{4}", "%m/%d/%Y")):
        if re.fullmatch(pattern, value):
            try:
                return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
            except ValueError:
                return None
    return None


# --- Cleaning rules (1-11) -------------------------------------------------------
def check_no_surrounding_whitespace(df):
    """1. No leading/trailing whitespace in any column."""
    bad = pd.Series(False, index=df.index)
    cols = []
    for col in df.columns:
        col_bad = df[col] != df[col].str.strip()
        if col_bad.any():
            cols.append(f"{col}={int(col_bad.sum())}")
        bad |= col_bad
    result = _from_mask(df, bad, "have untrimmed values")
    if cols:
        result.details += f" ({', '.join(cols)})"
    return result


def check_customer_name_title_case(df):
    """2. customer_name is Title Case."""
    if (m := _missing(df, "customer_name")):
        return m
    s = df["customer_name"].str.strip()
    return _from_mask(df, s != s.str.title(), "not Title Case")


def check_email_valid(df):
    """3. email is lowercase, non-empty, valid format."""
    if (m := _missing(df, "email")):
        return m
    return _from_mask(df, ~df["email"].str.fullmatch(EMAIL_PATTERN), "empty, not lowercase or invalid")


def check_phone_format(df):
    """4. phone is blank or matches ^04\\d{8}$."""
    if (m := _missing(df, "phone")):
        return m
    s = df["phone"]
    return _from_mask(df, (s != "") & ~s.str.fullmatch(PHONE_PATTERN), "not blank and not 04XXXXXXXX")


def check_state_valid(df):
    """5. state is blank or a valid Australian state/territory code."""
    if (m := _missing(df, "state")):
        return m
    s = df["state"]
    return _from_mask(df, (s != "") & ~s.isin(VALID_STATES), "not blank and not a state code")


def check_order_date_iso(df):
    """6. order_date matches YYYY-MM-DD and is a real date."""
    if (m := _missing(df, "order_date")):
        return m
    s = df["order_date"]
    bad = ~s.str.fullmatch(DATE_PATTERN) | s.map(parse_date).isna()
    return _from_mask(df, bad, "not a real YYYY-MM-DD date (incl. empty)")


def check_amount_format(df):
    """7. amount_usd is numeric, >= 0, with exactly 2 decimal places."""
    if (m := _missing(df, "amount_usd")):
        return m
    # the pattern has no '-', so it also enforces >= 0
    return _from_mask(df, ~df["amount_usd"].str.fullmatch(AMOUNT_PATTERN),
                      "not a non-negative number with 2 decimals")


def check_quantity_positive_int(df):
    """8. quantity is an integer >= 1."""
    if (m := _missing(df, "quantity")):
        return m
    s = df["quantity"]
    bad = ~s.str.fullmatch(r"\d+") | (pd.to_numeric(s, errors="coerce").fillna(0) < 1)
    return _from_mask(df, bad, "not an integer >= 1")


def check_status_valid(df):
    """9. status is one of pending/shipped/delivered/cancelled."""
    if (m := _missing(df, "status")):
        return m
    return _from_mask(df, ~df["status"].isin(VALID_STATUSES), "not an allowed status")


def check_order_id_not_empty(df):
    """10. No empty order_id."""
    if (m := _missing(df, "order_id")):
        return m
    return _from_mask(df, df["order_id"].str.strip() == "", "have an empty order_id")


def check_order_id_unique(df):
    """11. order_id is unique (blank ids are rule 10's job)."""
    if (m := _missing(df, "order_id")):
        return m
    s = df["order_id"]
    bad = (s.str.strip() != "") & s.duplicated(keep=False)
    return _from_mask(df, bad, "share an order_id with another row")


CLEANING_RULES = [
    ("R01 no surrounding whitespace", check_no_surrounding_whitespace),
    ("R02 customer_name Title Case", check_customer_name_title_case),
    ("R03 email valid + lowercase", check_email_valid),
    ("R04 phone blank or 04XXXXXXXX", check_phone_format),
    ("R05 state blank or valid code", check_state_valid),
    ("R06 order_date YYYY-MM-DD", check_order_date_iso),
    ("R07 amount_usd >= 0, 2dp", check_amount_format),
    ("R08 quantity integer >= 1", check_quantity_positive_int),
    ("R09 status valid", check_status_valid),
    ("R10 order_id not empty", check_order_id_not_empty),
    ("R11 order_id unique", check_order_id_unique),
]


# --- Semantic checks ---------------------------------------------------------------
def check_amount_in_baseline_range(df):
    """amount_usd stays within the baseline range (catches e.g. dollars -> cents)."""
    if (m := _missing(df, "amount_usd")):
        return m
    values = pd.to_numeric(df["amount_usd"], errors="coerce")
    bad = values.isna() | (values < AMOUNT_MIN) | (values > AMOUNT_MAX)
    return _from_mask(df, bad, f"not a number in {AMOUNT_MIN:g}-{AMOUNT_MAX:g}")


def check_dates_match_reference(df, reference_df):
    """order_date means the same day as in the reference file, for every order_id in both.
    Reference dates may be YYYY-MM-DD or MM/DD/YYYY (raw input or a cleaned output), so this
    catches dates that are valid but wrong, e.g. 02/03 read as 3 Feb instead of 2 Mar."""
    if (m := _missing(df, "order_id", "order_date")) or (m := _missing(reference_df, "order_id", "order_date")):
        return m
    expected = {}
    for oid, d in zip(reference_df["order_id"], reference_df["order_date"]):
        if id_key(oid) and (iso := parse_date(d)):
            expected.setdefault(id_key(oid), iso)
    compared = 0
    bad = pd.Series(False, index=df.index)
    for i, (oid, d) in enumerate(zip(df["order_id"], df["order_date"])):
        if (want := expected.get(id_key(oid))) is None:
            continue
        compared += 1
        if parse_date(d) != want:
            bad.iloc[i] = True
    if not compared:
        return CheckResult(False, "no order_id with a valid date in common with the reference", 0)
    result = _from_mask(df, bad, f"of {compared} comparable rows have a different date than the reference")
    if result.passed:
        result.details = f"{compared} comparable rows match the reference dates"
    return result


# --- Platform-behaviour checks ------------------------------------------------------
def check_order_id_integer_strings(df):
    """order_id must stay an integer string; '1001.0' means the platform coerced it to float."""
    if (m := _missing(df, "order_id")):
        return m
    s = df["order_id"]
    bad = (s != "") & ~s.str.fullmatch(ORDER_ID_PATTERN)
    result = _from_mask(df, bad, "not an integer string")
    if not result.passed and s[bad].str.fullmatch(r"\d+\.0+").all():
        result.details += " - integer ids were written as floats (e.g. 1001 -> 1001.0)"
    return result


def check_no_silent_nulling(df, input_df):
    """A value that was non-empty in the input must not be empty in the output,
    for the same order_id and column (rows matched via id_key)."""
    if (m := _missing(df, "order_id")) or (m := _missing(input_df, "order_id")):
        return m
    cols = [c for c in df.columns if c in input_df.columns and c != "order_id"]
    inp = input_df.assign(_key=input_df["order_id"].map(id_key))
    out = df.assign(_key=df["order_id"].map(id_key), _row=range(len(df)))
    merged = out.merge(inp[inp["_key"] != ""], on="_key", suffixes=("", "_in"))
    bad = pd.Series(False, index=df.index)
    examples = []
    for col in cols:
        hits = merged[(merged[f"{col}_in"].str.strip() != "") & (merged[col].str.strip() == "")]
        for _, row in hits.drop_duplicates(["_key"]).iterrows():
            bad.iloc[row["_row"]] = True
            examples.append(f"{row['order_id']}.{col}: {row[f'{col}_in']!r} -> ''")
    n = int(bad.sum())
    if not n:
        return CheckResult(True, f"no values blanked across {len(cols)} shared columns", 0)
    return CheckResult(False, f"{n} row(s) had a non-empty input value replaced by an empty one",
                       n, examples[:MAX_EXAMPLES])


def check_identical(df, input_df):
    """Pass-through identity: every cell of the output equals the input cell at the same position."""
    if list(df.columns) != list(input_df.columns):
        return CheckResult(False, f"columns differ: {list(df.columns)} vs input {list(input_df.columns)}")
    rows = min(len(df), len(input_df))
    per_column, examples, total = {}, [], 0
    for col in df.columns:
        a, b = input_df[col].iloc[:rows].to_numpy(), df[col].iloc[:rows].to_numpy()
        changed = [i for i in range(rows) if a[i] != b[i]]
        per_column[col] = {"changed": len(changed),
                           "example": f"{a[changed[0]]!r} -> {b[changed[0]]!r}" if changed else ""}
        total += len(changed)
        examples += [f"{_label(input_df, i)}.{col}: {a[i]!r} -> {b[i]!r}" for i in changed[:2]]
    details = f"{total} of {rows * len(df.columns)} cells changed"
    if len(df) != len(input_df):
        details += f"; row count differs ({len(df)} out vs {len(input_df)} in)"
    passed = total == 0 and len(df) == len(input_df)
    return CheckResult(passed, details, total, examples[:MAX_EXAMPLES], {"per_column": per_column})
