"""Cleaning rules and semantic checks for the orders dataset.

Every check takes a DataFrame (all values read as strings) and returns
(passed: bool, details: str). Checks are deliberately small and independent
so each failure points at exactly one rule.
"""
from datetime import datetime

import pandas as pd

# --- Thresholds / reference values ---------------------------------------------
TEXT_COLUMNS = ["customer_name", "email", "phone", "state", "order_date", "status"]
VALID_STATES = {"NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"}
VALID_STATUSES = {"pending", "shipped", "delivered", "cancelled"}
PHONE_PATTERN = r"^04\d{8}$"
EMAIL_PATTERN = r"^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$"
DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"
AMOUNT_PATTERN = r"^\d+\.\d{2}$"
AMOUNT_MIN = 5.00   # baseline range (semantic check)
AMOUNT_MAX = 500.00
MAX_EXAMPLES = 5    # how many offending values to show in details


def _missing(df: pd.DataFrame, col: str):
    if col not in df.columns:
        return False, f"column '{col}' is missing"
    return None


def _report(bad: pd.Series, df: pd.DataFrame, col: str, what: str):
    if not bad.any():
        return True, f"all {len(df)} rows OK"
    examples = df.loc[bad, col].head(MAX_EXAMPLES).tolist()
    return False, f"{int(bad.sum())} row(s) {what}; e.g. {examples}"


# --- Cleaning rules (1-11) -----------------------------------------------------
def check_no_surrounding_whitespace(df):
    """1. No leading/trailing whitespace in text columns."""
    problems = []
    for col in [c for c in TEXT_COLUMNS if c in df.columns]:
        n = int((df[col] != df[col].str.strip()).sum())
        if n:
            problems.append(f"{col}: {n}")
    return (not problems, "OK" if not problems else "untrimmed values -> " + ", ".join(problems))


def check_customer_name_title_case(df):
    """2. customer_name is Title Case."""
    if (m := _missing(df, "customer_name")):
        return m
    s = df["customer_name"]
    bad = (s != "") & (s != s.str.title())
    return _report(bad, df, "customer_name", "not Title Case")


def check_email_valid(df):
    """3. email is lowercase, non-empty, valid format."""
    if (m := _missing(df, "email")):
        return m
    s = df["email"]
    bad = ~s.str.fullmatch(EMAIL_PATTERN)
    return _report(bad, df, "email", "empty, not lowercase or invalid")


def check_phone_format(df):
    """4. phone is blank or matches ^04\\d{8}$."""
    if (m := _missing(df, "phone")):
        return m
    s = df["phone"]
    bad = (s != "") & ~s.str.fullmatch(PHONE_PATTERN)
    return _report(bad, df, "phone", "not blank and not 04XXXXXXXX")


def check_state_valid(df):
    """5. state is blank or a valid Australian state/territory code."""
    if (m := _missing(df, "state")):
        return m
    s = df["state"]
    bad = (s != "") & ~s.isin(VALID_STATES)
    return _report(bad, df, "state", "not a valid state code")


def _is_real_date(value: str) -> bool:
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def check_order_date_iso(df):
    """6. order_date matches YYYY-MM-DD and is a real date."""
    if (m := _missing(df, "order_date")):
        return m
    s = df["order_date"]
    bad = ~s.str.fullmatch(DATE_PATTERN) | ~s.map(_is_real_date)
    return _report(bad, df, "order_date", "not a real YYYY-MM-DD date")


def check_amount_format(df):
    """7. amount_usd is numeric, >= 0, with exactly 2 decimal places."""
    if (m := _missing(df, "amount_usd")):
        return m
    s = df["amount_usd"]
    bad = ~s.str.fullmatch(AMOUNT_PATTERN)  # pattern has no '-', so also enforces >= 0
    return _report(bad, df, "amount_usd", "not a non-negative number with 2 decimals")


def check_quantity_positive_int(df):
    """8. quantity is an integer >= 1."""
    if (m := _missing(df, "quantity")):
        return m
    s = df["quantity"]
    bad = ~s.str.fullmatch(r"\d+") | (pd.to_numeric(s, errors="coerce").fillna(0) < 1)
    return _report(bad, df, "quantity", "not an integer >= 1")


def check_status_valid(df):
    """9. status is one of pending/shipped/delivered/cancelled."""
    if (m := _missing(df, "status")):
        return m
    bad = ~df["status"].isin(VALID_STATUSES)
    return _report(bad, df, "status", "not an allowed status")


def check_order_id_not_empty(df):
    """10. No empty order_id."""
    if (m := _missing(df, "order_id")):
        return m
    bad = df["order_id"].str.strip() == ""
    return _report(bad, df, "order_id", "have an empty order_id")


def check_order_id_unique(df):
    """11. order_id is unique."""
    if (m := _missing(df, "order_id")):
        return m
    bad = df["order_id"].duplicated(keep=False)
    return _report(bad, df, "order_id", "share a duplicate order_id")


CLEANING_RULES = [
    ("R01 no surrounding whitespace", check_no_surrounding_whitespace),
    ("R02 customer_name Title Case", check_customer_name_title_case),
    ("R03 email valid + lowercase", check_email_valid),
    ("R04 phone blank or 04XXXXXXXX", check_phone_format),
    ("R05 state valid", check_state_valid),
    ("R06 order_date YYYY-MM-DD", check_order_date_iso),
    ("R07 amount_usd >= 0, 2dp", check_amount_format),
    ("R08 quantity integer >= 1", check_quantity_positive_int),
    ("R09 status valid", check_status_valid),
    ("R10 order_id not empty", check_order_id_not_empty),
    ("R11 order_id unique", check_order_id_unique),
]


# --- Semantic checks -------------------------------------------------------------
def check_amount_in_baseline_range(df):
    """amount_usd stays within the baseline range (catches e.g. dollars -> cents)."""
    if (m := _missing(df, "amount_usd")):
        return m
    s = df["amount_usd"]
    values = pd.to_numeric(s, errors="coerce")
    bad = values.isna() | (values < AMOUNT_MIN) | (values > AMOUNT_MAX)
    return _report(bad, df, "amount_usd", f"outside baseline range {AMOUNT_MIN}-{AMOUNT_MAX}")


def check_dates_match_baseline(df, baseline_df):
    """order_date equals the baseline's date for every order_id present in both
    (catches e.g. MM/DD read as DD/MM producing valid-looking but wrong dates)."""
    if baseline_df is None:
        return True, "SKIPPED: no --baseline given"
    for frame, name in ((df, "output"), (baseline_df, "baseline")):
        for col in ("order_id", "order_date"):
            if col not in frame.columns:
                return False, f"column '{col}' is missing from {name}"
    merged = df[["order_id", "order_date"]].merge(
        baseline_df[["order_id", "order_date"]], on="order_id", suffixes=("", "_baseline")
    )
    if merged.empty:
        return False, "no order_id values in common with the baseline"
    bad = merged["order_date"] != merged["order_date_baseline"]
    if not bad.any():
        return True, f"{len(merged)} shared rows match the baseline"
    examples = merged.loc[bad, ["order_id", "order_date", "order_date_baseline"]].head(MAX_EXAMPLES)
    return False, f"{int(bad.sum())}/{len(merged)} dates differ; e.g. {examples.to_dict('records')}"
