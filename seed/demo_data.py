"""Priya's synthetic demo data. Single source of truth for the seed, the PDFs and the tests.

Field names match the Convex schema (camelCase). Money is integer cents everywhere.
All data is synthetic; Priya Sharma is a made-up persona.
"""
from __future__ import annotations

from datetime import date, timedelta

RATE_CENTS = 1800  # $18.00 an hour
SS_RATE_BP = 620  # 6.20% in basis points
MEDICARE_RATE_BP = 145  # 1.45%
EMPLOYER = "University Dining Services"
PAYROLL_COUNTERPARTY = "University Dining Payroll"
FIRST_PERIOD_START = date(2026, 1, 12)  # a Monday
PAYSTUB_COUNT = 8
SPLIT_PAYSTUB = 5  # 1-based; its 40 hours are 16 + 24
REFUND_CENTS = 44064


def pct_of(cents: int, basis_points: int) -> int:
    """Integer percentage, rounded half up. 72000 * 620 bp = 4464."""
    return (cents * basis_points + 5000) // 10000


PROFILE = {
    "name": "Priya Sharma",
    "visa": "F-1",
    "arrivalDate": "2024-08-15",
    "school": "Golden Bear University",
    "homeCountry": "India",
    "homeCurrency": "INR",
    "workAuth": "on-campus",
    "phoneMasked": "(***) ***-4821",
    # Not in the starter Convex schema yet: the 8843 rule needs to know what she already filed.
    "filed8843Years": [2024, 2025],
}

SCHOOL_CALENDAR = {
    "school": "Golden Bear University",
    "sessions": [
        {"name": "Fall 2025", "start": "2025-08-27", "end": "2025-12-19"},
        {"name": "Spring 2026", "start": "2026-01-12", "end": "2026-05-15"},
        {"name": "Fall 2026", "start": "2026-08-26", "end": "2026-12-18"},
    ],
}


def make_paystub(index: int, period_start: date, hours_by_week: list[int]) -> dict:
    gross = sum(hours_by_week) * RATE_CENTS
    ss = pct_of(gross, SS_RATE_BP)
    medicare = pct_of(gross, MEDICARE_RATE_BP)
    return {
        "periodStart": period_start.isoformat(),
        "periodEnd": (period_start + timedelta(days=13)).isoformat(),
        "employer": EMPLOYER,
        "grossCents": gross,
        "hoursByWeek": hours_by_week,
        "ssCents": ss,
        "medicareCents": medicare,
        "netCents": gross - ss - medicare,
        "sourceFile": f"paystub_{index:02d}.pdf",
    }


def paystubs() -> list[dict]:
    stubs = []
    for i in range(1, PAYSTUB_COUNT + 1):
        start = FIRST_PERIOD_START + timedelta(days=14 * (i - 1))
        hours = [16, 24] if i == SPLIT_PAYSTUB else [20, 20]
        stubs.append(make_paystub(i, start, hours))
    return stubs


def payroll_deposits() -> list[dict]:
    """One deposit per paystub, 1 or 2 days after the period ends (alternating)."""
    deposits = []
    for i, stub in enumerate(paystubs()):
        paid = date.fromisoformat(stub["periodEnd"]) + timedelta(days=1 + i % 2)
        deposits.append({
            "kind": "deposit",
            "amountCents": stub["netCents"],
            "date": paid.isoformat(),
            "counterparty": PAYROLL_COUNTERPARTY,
            "memo": f"Payroll {stub['periodStart']} to {stub['periodEnd']}",
        })
    return deposits


def inr_to_usd_cents(inr: int, rate_hundredths: int) -> int:
    """INR amount at a rate in hundredths of a rupee per dollar, rounded half up to cents."""
    return (inr * 100 * 100 + rate_hundredths // 2) // rate_hundredths


# Rate received is worse than the (synthetic) market rate, so the Price agent can show the markup.
FAMILY_TRANSFERS = [
    {"date": "2026-01-05", "inr": 50000, "rateReceived": 8210, "marketRate": 8355},
    {"date": "2026-03-04", "inr": 50000, "rateReceived": 8195, "marketRate": 8340},
]


def family_transfers() -> list[dict]:
    out = []
    for t in FAMILY_TRANSFERS:
        out.append({
            "kind": "transfer_in",
            "amountCents": inr_to_usd_cents(t["inr"], t["rateReceived"]),
            "date": t["date"],
            "counterparty": "Family transfer - INR",
            "memo": f"INR {t['inr']} at {t['rateReceived'] / 100:.2f} INR/USD",
        })
    return out


# (date, merchant, category, cents). 20 purchases.
PURCHASES = [
    ("2026-01-08", "Telegraph Apartments", "rent", 80000),
    ("2026-01-10", "Campus Furniture Outlet", "furniture", 7000),  # the $70 table
    ("2026-01-14", "Berkeley Bowl Market", "groceries", 6342),
    ("2026-01-21", "Patel Brothers", "groceries", 4815),
    ("2026-01-28", "Mint Mobile", "phone", 3000),
    ("2026-02-01", "Telegraph Apartments", "rent", 80000),
    ("2026-02-04", "Berkeley Bowl Market", "groceries", 5527),
    ("2026-02-11", "Trader Joe's", "groceries", 3964),
    ("2026-02-18", "Patel Brothers", "groceries", 5210),
    ("2026-02-28", "Mint Mobile", "phone", 3000),
    ("2026-03-01", "Telegraph Apartments", "rent", 80000),
    ("2026-03-07", "Trader Joe's", "groceries", 4488),
    ("2026-03-15", "Cal Student Store", "books", 2899),
    ("2026-03-21", "Berkeley Bowl Market", "groceries", 6120),
    ("2026-03-28", "Mint Mobile", "phone", 3000),
    ("2026-04-01", "Telegraph Apartments", "rent", 80000),
    ("2026-04-09", "Patel Brothers", "groceries", 4732),
    ("2026-04-18", "Trader Joe's", "groceries", 3851),
    ("2026-04-28", "Mint Mobile", "phone", 3000),
    ("2026-05-01", "Telegraph Apartments", "rent", 80000),
]


def purchases() -> list[dict]:
    return [
        {"kind": "purchase", "amountCents": cents, "date": d, "counterparty": merchant, "memo": category}
        for d, merchant, category, cents in PURCHASES
    ]


# Released only by "simulate 2 weeks", so the refund match fires live.
HIDDEN_REFUND = {
    "kind": "deposit",
    "amountCents": REFUND_CENTS,
    "counterparty": PAYROLL_COUNTERPARTY,
    "memo": "FICA refund",
}


def transactions() -> list[dict]:
    """Everything visible at seed time, oldest first. Excludes the hidden refund."""
    return sorted(payroll_deposits() + family_transfers() + purchases(), key=lambda t: t["date"])
