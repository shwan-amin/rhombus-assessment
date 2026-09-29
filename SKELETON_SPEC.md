# Task: generate the repository skeleton

I'm doing a QA take-home assessment for Rhombus AI, a no-code ETL/DataOps platform. The pipeline under test is:
**S3 source → cleaning pipeline built by the Rhombus AI builder → Google Cloud Storage destination, run on a schedule.**
I then change the input file on purpose (schema drift and semantic drift) and record how the platform reacts.

Please create the **skeleton** of the repository in the current directory: folders, config files, templates and placeholder files. The actual test logic comes later, once I've captured the real UI selectors and API requests.

## Hard rules

- **Do not run any git commands.** No `git init`, `git add`, `git commit`, `git remote` or `git push`. I'll handle git and GitHub myself.
- **Do not install dependencies** (`npm install`, `pip install`) unless I ask. Just write the files that declare them.
- **Do not invent selectors, URLs, API endpoints or credentials.** Where real values are needed, leave a clearly marked `TODO` and a placeholder.
- **Never write real secrets anywhere.** Only `.env.example` with empty values.
- If a folder or file already exists (for example `datasets/` or `README.md`), **don't overwrite it**. Tell me what you skipped.
- When you're finished, print a tree of what you created and list every `TODO` I need to fill in.

## Target structure

```
.
├── README.md
├── .gitignore
├── .env.example
├── ui-tests/
│   ├── package.json
│   ├── playwright.config.ts
│   ├── tsconfig.json
│   ├── tests/
│   │   ├── auth.setup.ts
│   │   └── pipeline-journey.spec.ts
│   └── pages/
│       └── README.md
├── api-tests/
│   ├── requirements.txt
│   ├── conftest.py
│   ├── test_api_positive.py
│   └── test_api_negative.py
├── data-validation/
│   ├── requirements.txt
│   ├── validate.py
│   ├── rules.py
│   └── results/
│       └── .gitkeep
├── datasets/
│   └── .gitkeep
├── observations/
│   ├── _TEMPLATE.md
│   ├── schema-drop-column.md
│   ├── schema-rename-column.md
│   ├── schema-change-type.md
│   ├── schema-add-column.md
│   ├── schema-combined.md
│   ├── semantic-dollars-to-cents.md
│   ├── semantic-date-mmdd-to-ddmm.md
│   └── evidence/
│       └── .gitkeep
└── dashboard/
    └── .gitkeep
```

## File details

### `.gitignore`

Must cover: `.env`, any `*.json` credentials (`*service-account*.json`, `*-key.json`, `gcp*.json`), `*credentials*.csv`, `*accessKeys*.csv`, `node_modules/`, `__pycache__/`, `.venv/`, `.pytest_cache/`, Playwright output (`test-results/`, `playwright-report/`, `playwright/.auth/`), `data-validation/results/*` except `.gitkeep`, and `.DS_Store`.

### `.env.example`

Empty values with a one-line comment each:

```
# Rhombus AI
RHOMBUS_BASE_URL=https://rhombusai.com
RHOMBUS_EMAIL=
RHOMBUS_PASSWORD=
RHOMBUS_API_BASE_URL=        # TODO: from the browser network tab
RHOMBUS_AUTH_TOKEN=          # TODO: from the browser network tab (for API tests)

# AWS (source)
AWS_REGION=ap-southeast-2
S3_BUCKET=rhombus-qa-source-shwan
S3_INPUT_KEY=input/orders.csv
AWS_PROFILE=                 # local AWS CLI profile used by the scripts

# GCP (destination)
GCS_BUCKET=rhombus-qa-dest-shwan
GCS_OUTPUT_PREFIX=           # TODO: output filename or prefix Rhombus writes to
GOOGLE_APPLICATION_CREDENTIALS=   # path OUTSIDE this repo, or leave blank to use gcloud login
```

### `ui-tests/` (Playwright + TypeScript)

- `package.json`: `@playwright/test`, `dotenv`, `typescript`. Scripts: `test`, `test:headed`, `report`.
- `playwright.config.ts`:
  - load `../.env`
  - use a `setup` project that runs `auth.setup.ts` and saves `storageState` to `playwright/.auth/user.json`, which the main project reuses
  - Chromium only
  - `trace: 'on-first-retry'`, `screenshot: 'only-on-failure'`, `video: 'retain-on-failure'`
  - sensible `expect` timeout, and longer timeouts for the pipeline run
- `auth.setup.ts`: log in with `RHOMBUS_EMAIL` / `RHOMBUS_PASSWORD` and save the storage state. Selectors are `TODO`s.
- `pipeline-journey.spec.ts`: one `test.describe` with `test.step` blocks for:
  1. open the project
  2. configure the S3 data input
  3. build the cleaning pipeline through the AI builder prompt
  4. set the GCS destination
  5. configure the schedule
  6. trigger a run and assert the logs show success

  Each step has a `TODO` for selectors and a comment describing the assertion to make on a *real outcome*, e.g. the node shows a success status, or the schedule shows as active.
  - **No `waitForTimeout` anywhere.** Add a top-of-file comment explaining that waits must use web-first assertions (`expect(...).toBeVisible()`) or `expect.poll`.
  - Put the AI builder prompt in a constant loaded from a text file, `ui-tests/fixtures/ai-builder-prompt.txt`. Create that file with a `TODO: paste prompt from datasets/README.md` line.
- `pages/README.md`: a short note that page objects go here once selectors are known.

### `api-tests/` (pytest + requests)

- `requirements.txt`: `pytest`, `requests`, `python-dotenv`.
- `conftest.py`: load `../.env`, and provide fixtures `base_url`, `auth_headers` and `unauth_session`. Skip tests with a clear message if the required env vars are missing.
- `test_api_positive.py`: two test functions with `TODO` endpoints, e.g. list projects/pipelines and get one pipeline's details. Assert on both the status code **and** specific fields in the JSON body.
- `test_api_negative.py`: three tests:
  - no auth header → expect 401/403
  - invalid/expired token → expect 401/403
  - request for a non-existent resource ID → expect 404, or document what is actually returned

  Assert on the status code and the error body.

### `data-validation/` (Python)

- `requirements.txt`: `pandas`, `boto3`, `google-cloud-storage`, `python-dotenv`.
- `rules.py`: the 11 cleaning rules as small, separate check functions. Each takes a DataFrame and returns `(passed: bool, details: str)`:
  1. no leading/trailing whitespace in text columns
  2. `customer_name` is Title Case
  3. `email` is lowercase, non-empty, valid format
  4. `phone` is blank or matches `^04\d{8}$`
  5. `state` is blank or one of NSW/VIC/QLD/WA/SA/TAS/ACT/NT
  6. `order_date` matches `YYYY-MM-DD` and is a real date
  7. `amount_usd` is numeric, ≥ 0, 2 decimal places
  8. `quantity` is an integer ≥ 1
  9. `status` is one of pending/shipped/delivered/cancelled
  10. no empty `order_id`
  11. `order_id` is unique

  Also write semantic checks:
  - `amount_usd` within the baseline range (5 to 500)
  - `order_date` values match the dates expected from the baseline, for rows present in both

  Leave the thresholds as named constants at the top.
- `validate.py`: a CLI.
  - `python validate.py --scenario baseline --input <local path or s3://...> --output <local path or gs://...> [--expected-rows 28] [--compare-with <previous output>]`
  - Download from S3/GCS when given a URI, otherwise read local files.
  - Run these checks:
    - **schema**: expected columns and order
    - **row count** vs `--expected-rows`
    - **all cleaning rules**
    - **semantic checks**
    - **determinism**: SHA-256 of the normalised output compared with `--compare-with`, reporting the row-level diff if they differ
  - Print a readable PASS/FAIL table, save a JSON report to `results/<scenario>-<timestamp>.json`, and exit non-zero on any failure.
  - It's fine for this to be real, working code. Just keep it simple and readable.

### `datasets/`

Leave only `.gitkeep`. I'll copy my own files in.

### `observations/`

`_TEMPLATE.md` has these sections:
- **Change made** (link to the dataset file)
- **Expected behaviour**
- **Steps to reproduce** (numbered)
- **What happened**: did the pipeline stop, warn, or continue? What reached GCS?
- **Logs** (excerpt + link to evidence)
- **Chatbot diagnosis**: what it said, and whether it was correct
- **Chatbot fix**: what it suggested, and whether it worked
- **Schedule afterwards**
- **Validation result** (link to the JSON report)
- **Severity**: Critical / High / Medium / Low, with one line of reasoning

Create the 7 case files listed above as copies of the template, with the title and "Change made" pre-filled:

| File | Change |
|---|---|
| `schema-drop-column` | `phone` column removed |
| `schema-rename-column` | `email` → `email_address` |
| `schema-change-type` | `order_id` integer → string `ORD-1001` |
| `schema-add-column` | new `discount_code` column |
| `schema-combined` | all four changes |
| `semantic-dollars-to-cents` | `amount_usd` ×100 |
| `semantic-date-mmdd-to-ddmm` | dates written as DD/MM/YYYY |

### `README.md`

Use these sections, with `TODO` placeholders where I'll fill in content:

1. **Title and one-paragraph overview** of the pipeline under test (S3 → AI-built cleaning → GCS, scheduled).
2. **Repository structure**: a short tree with a one-line description per folder.
3. **Setup and how to run**, with prerequisites (Node, Python 3.11+, AWS CLI profile, gcloud login) and then a subsection per suite with exact commands:
   - `cd ui-tests && npm install && npx playwright install chromium && npm test`
   - `cd api-tests && pip install -r requirements.txt && pytest -v`
   - `cd data-validation && pip install -r requirements.txt && python validate.py ...` (with an example for the baseline and one for a drift case)
   - Note that credentials go in `.env`, copied from `.env.example`, and must never be committed.
4. **Setup notes / environment decisions**: a bullet list with these entries pre-filled as `TODO` headings:
   - least-privilege S3 access via the generated bucket policy
   - GCS service account and org-policy key block
   - chatbot said GCS was not a supported destination, but the UI offers it
5. **Observations summary**: a table with columns `Case | Change | Pipeline stopped? | Chatbot fix worked? | Severity | Details`. One row per drift case, with the Details column linking to its file in `observations/`. Leave the result cells as `TODO`. Below the table, a **Top 3 findings** list with `TODO` items.
6. **Usability feedback**: a `TODO` placeholder for 1–2 paragraphs covering what was helpful, what was frustrating, and suggestions.
7. **Demo video**: `TODO: link`.
8. **Optional: observability dashboard**: `TODO: link`.
9. **AI assistance**: one line, left as `TODO`, where I'll state how AI tools were used.
