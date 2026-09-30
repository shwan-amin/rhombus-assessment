# Schema drift: add column

## Change made

A new `discount_code` column was added. Dataset: [`datasets/schema_add_column.csv`](../datasets/schema_add_column.csv)

## Expected behaviour

TODO: what a robust pipeline should do (stop / warn / continue) and what should reach GCS.

## Steps to reproduce

1. TODO: upload the modified file to `s3://<S3_BUCKET>/<S3_INPUT_KEY>`
2. TODO: trigger the pipeline (scheduled run or "run now")
3. TODO: inspect the run logs and the GCS output
4. TODO: run `data-validation/validate.py` against the output

## What happened

TODO: did the pipeline stop, warn, or continue? What reached GCS?

## Logs

```
TODO: log excerpt
```

Evidence: [TODO](evidence/TODO)

## Chatbot diagnosis

TODO: what it said, and whether it was correct.

## Chatbot fix

TODO: what it suggested, and whether it worked.

## Schedule afterwards

TODO: is the schedule still active? Did the next scheduled run succeed, fail, or get skipped?

## Validation result

TODO: PASS/FAIL summary. Report: [`data-validation/results/TODO.json`](../data-validation/results/TODO.json)

## Severity

TODO: Critical / High / Medium / Low — one line of reasoning.
