"""Generate the messy baseline CSV and every drifted version.

Deterministic: no randomness, so re-running produces byte-identical files.
Run:  python3 datasets/make_datasets.py
"""
import csv
import re
from pathlib import Path

OUT = Path(__file__).parent
HEADER = ["order_id", "customer_name", "email", "phone", "state",
          "order_date", "amount_usd", "quantity", "status"]

# Clean "truth" rows: (id, name, email, phone, state, date MM/DD/YYYY, amount USD, qty, status)
CLEAN = [
    (1001, "Alice Smith", "alice.smith@example.com", "0412345678", "NSW", "01/15/2026", 49.99, 2, "shipped"),
    (1002, "Bob Jones", "bob.jones@example.com", "0423456789", "VIC", "01/22/2026", 120.00, 1, "delivered"),
    (1003, "Carla Nguyen", "carla.nguyen@example.com", "0434567890", "QLD", "02/03/2026", 15.50, 4, "pending"),
    (1004, "David Lee", "david.lee@example.com", "0445678901", "WA", "02/14/2026", 310.25, 1, "shipped"),
    (1005, "Emma Brown", "emma.brown@example.com", "0456789012", "SA", "02/28/2026", 75.00, 3, "cancelled"),
    (1006, "Farid Khan", "farid.khan@example.com", "0467890123", "NSW", "03/05/2026", 8.95, 6, "delivered"),
    (1007, "Grace Kim", "grace.kim@example.com", "0478901234", "TAS", "03/19/2026", 499.00, 1, "shipped"),
    (1008, "Hugo Martin", "hugo.martin@example.com", "0489012345", "ACT", "03/25/2026", 62.40, 2, "pending"),
    (1009, "Isla Wilson", "isla.wilson@example.com", "0490123456", "NT", "04/02/2026", 230.10, 1, "delivered"),
    (1010, "Jack Taylor", "jack.taylor@example.com", "0401234567", "VIC", "04/17/2026", 19.99, 5, "shipped"),
    (1011, "Kira Patel", "kira.patel@example.com", "0411223344", "QLD", "04/30/2026", 88.80, 2, "delivered"),
    (1012, "Liam Chen", "liam.chen@example.com", "0422334455", "NSW", "05/06/2026", 145.00, 1, "pending"),
    (1013, "Mia Rossi", "mia.rossi@example.com", "0433445566", "WA", "05/21/2026", 33.33, 3, "shipped"),
    (1014, "Noah Evans", "noah.evans@example.com", "0444556677", "SA", "06/09/2026", 275.50, 1, "cancelled"),
    (1015, "Olivia Park", "olivia.park@example.com", "0455667788", "NSW", "06/13/2026", 12.00, 8, "delivered"),
    (1016, "Pedro Alves", "pedro.alves@example.com", "0466778899", "VIC", "06/27/2026", 410.75, 1, "shipped"),
    (1017, "Quinn Adams", "quinn.adams@example.com", "0477889900", "QLD", "07/04/2026", 54.20, 2, "pending"),
    (1018, "Ruby Walsh", "ruby.walsh@example.com", "0488990011", "TAS", "07/16/2026", 99.99, 1, "delivered"),
    (1019, "Sam Wright", "sam.wright@example.com", "0499001122", "NSW", "07/29/2026", 187.60, 2, "shipped"),
    (1020, "Tara Singh", "tara.singh@example.com", "0400112233", "ACT", "08/08/2026", 24.50, 4, "delivered"),
    (1021, "Umar Ali", "umar.ali@example.com", "0410203040", "VIC", "08/19/2026", 360.00, 1, "pending"),
    (1022, "Vera Novak", "vera.novak@example.com", "0420304050", "WA", "08/23/2026", 45.45, 3, "shipped"),
    (1023, "Will Hart", "will.hart@example.com", "0430405060", "NSW", "09/01/2026", 150.00, 2, "delivered"),
    (1024, "Xin Zhao", "xin.zhao@example.com", "0440506070", "SA", "09/14/2026", 5.00, 10, "cancelled"),
    (1025, "Yara Haddad", "yara.haddad@example.com", "0450607080", "QLD", "09/18/2026", 220.20, 1, "shipped"),
    (1026, "Zoe Clarke", "zoe.clarke@example.com", "0460708090", "NSW", "09/26/2026", 67.89, 2, "delivered"),
]

STATE_VARIANTS = {
    "NSW": ["NSW", "nsw", " New South Wales"], "VIC": ["VIC", "Victoria", "vic "],
    "QLD": ["QLD", "Queensland"], "WA": ["WA", "wa"], "SA": ["SA", "South Australia"],
    "TAS": ["TAS", "Tasmania"], "ACT": ["ACT", "act"], "NT": ["NT", "Northern Territory"],
}


def fmt_phone(p, style):
    if style == 0:
        return f"{p[:4]} {p[4:7]} {p[7:]}"      # 0412 345 678
    if style == 1:
        return "+61" + p[1:]                     # +61412345678
    if style == 2:
        return f"{p[:4]}-{p[4:7]}-{p[7:]}"      # 0412-345-678
    return p                                     # 0412345678


def to_iso(mmdd):
    m, d, y = mmdd.split("/")
    return f"{y}-{m}-{d}"


def build_baseline():
    rows = []
    for i, (oid, name, email, phone, state, date, amt, qty, status) in enumerate(CLEAN):
        n = name if i % 3 else (name.upper() if i % 2 else name.lower())  # inconsistent case
        e = email if i % 4 else "  " + email.upper() + " "                 # case + whitespace
        ph = fmt_phone(phone, i % 4)                                        # 4 phone formats
        stv = STATE_VARIANTS[state][i % len(STATE_VARIANTS[state])]         # state spellings
        dt = to_iso(date) if i % 5 == 0 else date                           # mixed date formats
        st = status if i % 3 else status.upper() + " "                      # status case/space
        rows.append([str(oid), n, e, ph, stv, dt, f"{amt:.2f}", str(qty), st])

    # Duplicates
    rows.insert(3, list(rows[0]))    # exact duplicate of order 1001
    rows.insert(8, list(rows[5]))    # exact duplicate of order 1005
    near = list(rows[10])            # near-duplicate: same order_id, different case/whitespace
    near[2] = near[2].strip().upper()
    near[1] = near[1] + "  "
    rows.insert(12, near)

    # Missing / invalid values (one problem per row so each rule is testable in isolation)
    rows += [
        ["1027", "Aaron Bell", "", "0411000111", "NSW", "09/27/2026", "40.00", "1", "pending"],                  # missing email
        ["1028", "Bella Ford", "bella.ford@example", "0411000222", "VIC", "09/27/2026", "55.00", "2", "shipped"],  # invalid email
        ["1029", "Cody Grant", "cody.grant@example.com", "0411000333", "QLD", "09/28/2026", "", "1", "pending"],   # missing amount
        ["1030", "Dana Hill", "dana.hill@example.com", "0411000444", "WA", "09/28/2026", "-25.00", "1", "delivered"],  # negative amount
        ["1031", "Eli Irwin", "eli.irwin@example.com", "0411000555", "SA", "09/28/2026", "twelve", "1", "shipped"],    # non-numeric amount
        ["1032", "Fay Jensen", "fay.jensen@example.com", "0411000666", "TAS", "13/45/2026", "30.00", "1", "pending"],  # invalid date
        ["1033", "Gus King", "gus.king@example.com", "0411000777", "ACT", "09/29/2026", "70.00", "0", "shipped"],      # zero quantity
        ["1034", "Hana Lowe", "hana.lowe@example.com", "0411000888", "NT", "09/29/2026", "80.00", "abc", "delivered"], # non-numeric qty
        ["", "Ivan Moss", "ivan.moss@example.com", "0411000999", "NSW", "09/29/2026", "90.00", "1", "pending"],         # missing order_id
        ["1035", "June Nash", "june.nash@example.com", "", "VIC", "09/29/2026", "35.00", "2", "shipped"],              # missing phone (kept)
        ["1036", "Kai Owen", "kai.owen@example.com", "0412999888", "", "09/29/2026", "65.00", "1", "pending"],        # missing state (kept)
        ["1037", "Lena Price", "lena.price@example.com", "0412999777", "QLD", "09/29/2026", "42.00", "2", "unknown"],  # invalid status
    ]
    return rows


def write(name, header, data):
    with open(OUT / name, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(data)


# ---------- Schema drift helpers ----------
def drop_col(h, d, c):
    i = h.index(c)
    return [x for x in h if x != c], [[v for j, v in enumerate(r) if j != i] for r in d]


def rename_col(h, d, old, new):
    return [new if x == old else x for x in h], d


def change_type(h, d):
    """order_id: integer -> string with a prefix (1001 -> ORD-1001)."""
    i = h.index("order_id")
    return h, [[("ORD-" + v if (j == i and v) else v) for j, v in enumerate(r)] for r in d]


def add_col(h, d):
    codes = ["", "SPRING10", "", "VIP20", "", "", "WELCOME5"]
    return h + ["discount_code"], [r + [codes[k % len(codes)]] for k, r in enumerate(d)]


# ---------- Semantic drift helpers ----------
def dollars_to_cents(r, col):
    r = list(r)
    v = r[col["amount_usd"]]
    try:
        r[col["amount_usd"]] = str(int(round(float(v) * 100)))
    except ValueError:
        pass  # leave blanks / invalid values as they were
    return r


def mmdd_to_ddmm(r, col):
    r = list(r)
    v = r[col["order_date"]]
    us = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", v)
    iso = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", v)
    if us and int(us.group(1)) <= 12:
        r[col["order_date"]] = f"{us.group(2)}/{us.group(1)}/{us.group(3)}"
    elif iso:
        r[col["order_date"]] = f"{iso.group(3)}/{iso.group(2)}/{iso.group(1)}"
    return r


def main():
    rows = build_baseline()
    col = {h: i for i, h in enumerate(HEADER)}

    write("baseline_orders.csv", HEADER, rows)

    h, d = drop_col(HEADER, rows, "phone")
    write("schema_drop_column.csv", h, d)
    h, d = rename_col(HEADER, rows, "email", "email_address")
    write("schema_rename_column.csv", h, d)
    h, d = change_type(HEADER, rows)
    write("schema_change_type.csv", h, d)
    h, d = add_col(HEADER, rows)
    write("schema_add_column.csv", h, d)

    h, d = drop_col(HEADER, rows, "phone")
    h, d = rename_col(h, d, "email", "email_address")
    h, d = change_type(h, d)
    h, d = add_col(h, d)
    write("schema_combined.csv", h, d)

    write("semantic_dollars_to_cents.csv", HEADER, [dollars_to_cents(r, col) for r in rows])
    write("semantic_date_mmdd_to_ddmm.csv", HEADER, [mmdd_to_ddmm(r, col) for r in rows])

    print(f"baseline rows: {len(rows)}")


if __name__ == "__main__":
    main()
