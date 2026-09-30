# Baseline: pass-through pipeline with no transformations

> **Headline finding:** a pass-through pipeline modifies data without being asked. `order_id` became a float (`1001` → `1001.0`), dates were reformatted (`01/22/2026` → `2026-01-22`), and the invalid date `13/45/2026` was silently replaced with an empty value.

## Change made

Nothing in the data. The pipeline had only **Data Input → Data Output**, with no transformation nodes. Dataset: [`datasets/baseline_orders.csv`](../datasets/baseline_orders.csv) (41 rows), unmodified.

## Expected behaviour

The output is byte-for-byte identical to the input: 41 rows, same columns in the same order, and every value unchanged. That includes the planted problems (duplicates, bad casing, invalid rows), because nothing was asked to clean them.

## Steps to reproduce

1. Upload `datasets/baseline_orders.csv` to the S3 input key (`input/orders.csv`).
2. In a new Rhombus AI project, add a Data Input node for the S3 file and connect it directly to a Data Output node (GCS). Add no transformation nodes.
3. Run the pipeline and download the output file.
4. Validate it:
   ```bash
   .venv/bin/python data-validation/validate.py --scenario passthrough-identity \
     --input datasets/baseline_orders.csv \
     --output observations/evidence/runs/passthrough-output.csv \
     --expected-rows 28 --expect-identical
   ```

## What happened

The pipeline **continued** with no errors or warnings shown, and wrote a 41-row file to the destination. The row count and column order were preserved, but the platform changed values on its own:

| What I observed | Flagged by |
|---|---|
| 41 rows out (41 in); the cleaned baseline expects 28 | `row count` |
| Exact duplicates kept (1001 ×2, 1005 ×2) and near-duplicate kept (1009 ×2) | `R11 order_id unique` |
| `order_id` changed from `1001` to `1001.0` in every row (40 rows; the blank id stayed blank) | `P01 order_id stays integer`, `I01` |
| With no transform nodes, `order_date` was still rewritten from `MM/DD/YYYY` to `YYYY-MM-DD` (33 rows) — an unrequested change | `I01 output identical to input` |
| Names, emails, phones, states and status untouched (e.g. `  ALICE.SMITH@EXAMPLE.COM `, `SHIPPED `, `Victoria`, `+61423456789`) | `R01`–`R05`, `R09` |
| Order 1032's invalid date `13/45/2026` became an empty string instead of the row being dropped | `P02 no silent nulling`, `R06` |
| Invalid rows kept: missing email (1027), invalid email (1028), missing/negative/non-numeric amount (1029–1031), zero/non-numeric qty (1033–1034), missing `order_id` (Ivan Moss), invalid status (1037) | `R03`, `R07`, `R08`, `R09`, `R10` |

Changed cells per column (output vs input, same row position), from `--expect-identical`:

| Column | Changed | Example |
|---|---:|---|
| `order_id` | 40 | `'1001'` → `'1001.0'` |
| `order_date` | 34 | `'01/22/2026'` → `'2026-01-22'` (33 reformatted + 1032 blanked) |
| all other columns | 0 | |

**74 of 369 cells changed.** The reformatted dates still mean the same day (`S02 order_date same day as reference` passes for all 39 comparable rows), so the date change is a format change rather than data loss. The one exception is order 1032, whose value was lost.

**Validator summary:** 3 passed, 16 failed (exit code 1). The failures are expected for a pipeline with no cleaning (row count, R01–R11, S01). The ones that matter for this case are `P01` (type coercion), `P02` (silent nulling) and `I01` (identity). Report: [`evidence/passthrough-validation.json`](evidence/passthrough-validation.json).

## Logs

```
TODO: log excerpt from the run
```

Evidence:
- Output file: [`evidence/runs/passthrough-output.csv`](evidence/runs/passthrough-output.csv)
- Canvas screenshot: [`evidence/runs/passthrough-canvas.png`](evidence/runs/passthrough-canvas.png)
- TODO: further screenshots (run log, output preview)

## Chatbot diagnosis

TODO: if asked about this, what the chatbot said, and whether it was correct.

## Chatbot fix

TODO: what it suggested, and whether it worked.

## Schedule afterwards

TODO: not scheduled for this run, or note otherwise.

## Validation result

FAIL: 3 passed, 16 failed. Report: [`evidence/passthrough-validation.json`](evidence/passthrough-validation.json) (a copy of `data-validation/results/passthrough-identity-20260930T102128Z.json`, which is gitignored).

## Severity

TODO: Critical / High / Medium / Low — one line of reasoning.
