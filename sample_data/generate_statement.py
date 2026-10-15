"""
sample_data/generate_statement.py
Generates a fictional 150-row bank statement CSV for the Saath demo.
Synthetic data only — no real persons, no real institutions.
"""
import csv
import random
import os
from datetime import date, timedelta

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "sharma_bank_statement.csv")

random.seed(42)

START_DATE = date(2024, 10, 1)
END_DATE   = date(2025, 9, 30)

# ── PLANTED ASSETS (must be detected) ──────────────────────────────────
PLANTED = [
    # 1. Life insurance premium debit — monthly, fixed amount, distinctive payee
    {
        "type": "insurance_premium",
        "day_of_month": 5,
        "description": "AUTOPAY EXAMPLE LIFE INS PREMIUM POL-XXXXXXXX",
        "amount": 3200.00,
        "cr_dr": "DR",
    },
    # 2. SIP debit — monthly, fixed amount, SIP marker
    {
        "type": "sip",
        "day_of_month": 10,
        "description": "NACH DR SAMPLE AMC SIP FOLIO-XXXXXXXX",
        "amount": 5000.00,
        "cr_dr": "DR",
    },
    # 3. Employer salary credit — monthly, large fixed credit, employer name
    {
        "type": "salary",
        "day_of_month": 28,
        "description": "NEFT CR DEMO TECH PVT LTD SALARY",
        "amount": 67500.00,
        "cr_dr": "CR",
    },
]

# ── DECOY ROWS (should NOT be flagged as assets) ─────────────────────
DECOYS = [
    # Recurring but NOT an asset — utility bill
    {"day_of_month": 15, "description": "AUTOPAY CITY ELECTRICITY BOARD BILL", "amount": 820.00, "cr_dr": "DR"},
    # Grocery recurring
    {"day_of_month": 3,  "description": "UPI-FRESH MART GROCERY STORE",         "amount": 2300.00, "cr_dr": "DR"},
    # A debit with a similar pattern to insurance but it's a club membership
    {"day_of_month": 7,  "description": "AUTOPAY FITNESS FIRST CLUB MEMBERSHIP", "amount": 1999.00, "cr_dr": "DR"},
    # OTT subscription
    {"day_of_month": 12, "description": "AUTOPAY STREAMFLIX SUBSCRIPTION",       "amount": 199.00, "cr_dr": "DR"},
]

RANDOM_DEBITS = [
    ("ATM WITHDRAWAL", 500, 3000),
    ("UPI-ONLINE SHOPPING", 200, 8000),
    ("SWIGGY FOOD ORDER", 150, 600),
    ("PETROL PUMP PUNE", 500, 2000),
    ("MEDICAL PHARMACY", 200, 1500),
    ("UPI-MOBILE RECHARGE", 199, 599),
    ("AMAZON PAY", 100, 5000),
]

RANDOM_CREDITS = [
    ("UPI REFUND", 100, 500),
    ("INTEREST CR SAVINGS", 50, 300),
]


def all_months():
    d = START_DATE.replace(day=1)
    while d <= END_DATE:
        yield d.year, d.month
        if d.month == 12:
            d = d.replace(year=d.year+1, month=1)
        else:
            d = d.replace(month=d.month+1)


def clamp_day(year, month, day):
    import calendar
    last = calendar.monthrange(year, month)[1]
    return min(day, last)


rows = []

for year, month in all_months():
    # Planted assets
    for p in PLANTED:
        day = clamp_day(year, month, p["day_of_month"])
        rows.append({
            "Date": date(year, month, day).strftime("%d-%m-%Y"),
            "Description": p["description"],
            "Amount": p["amount"],
            "CR/DR": p["cr_dr"],
            "Balance": 0.0,  # filled later
        })

    # Decoys (every month)
    for d in DECOYS:
        day = clamp_day(year, month, d["day_of_month"])
        rows.append({
            "Date": date(year, month, day).strftime("%d-%m-%Y"),
            "Description": d["description"],
            "Amount": d["amount"],
            "CR/DR": d["cr_dr"],
            "Balance": 0.0,
        })

    # Random rows (5–8 per month)
    n_random = random.randint(5, 8)
    for _ in range(n_random):
        day = random.randint(1, 28)
        if random.random() < 0.8:
            desc, lo, hi = random.choice(RANDOM_DEBITS)
            amt = round(random.uniform(lo, hi), 2)
            cr_dr = "DR"
        else:
            desc, lo, hi = random.choice(RANDOM_CREDITS)
            amt = round(random.uniform(lo, hi), 2)
            cr_dr = "CR"
        rows.append({
            "Date": date(year, month, day).strftime("%d-%m-%Y"),
            "Description": desc,
            "Amount": amt,
            "CR/DR": cr_dr,
            "Balance": 0.0,
        })

# Sort by date
rows.sort(key=lambda r: r["Date"])

# Compute running balance (start at 1,50,000)
balance = 150000.00
for r in rows:
    if r["CR/DR"] == "CR":
        balance += r["Amount"]
    else:
        balance -= r["Amount"]
    r["Balance"] = round(balance, 2)

# Write
with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["Date", "Description", "Amount", "CR/DR", "Balance"])
    writer.writeheader()
    writer.writerows(rows)

print(f"✅ Generated {len(rows)} rows → {OUTPUT_FILE}")
