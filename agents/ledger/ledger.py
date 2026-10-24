"""Ledger rules: turn raw bank rows and transcribed paystubs into clean, checked rows.

Pure functions, integer cents. Claude never computes anything that lands here.
"""
from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

PAYROLL_MARKER = "Payroll"
FAMILY_MARKER = "Family transfer"
DEPOSIT_WINDOW_DAYS = 3
REFUND_TOLERANCE_CENTS = 100  # "within $1"
SS_RATE_BP = 620
MEDICARE_RATE_BP = 145
REFUND_PENDING_STATE = "awaiting_response"  # cases:refundReceived only accepts this state


def to_cents(amount) -> int:
    """Nessie dollars (float) or a printed amount ("$1,234.56") to integer cents."""
    if isinstance(amount, str):
        cleaned = re.sub(r"[$,\s]", "", amount)
        if not re.fullmatch(r"-?\d+(\.\d{1,2})?", cleaned):
            raise ValueError(f"not a money amount: {amount!r}")
        amount = cleaned
    return int((Decimal(str(amount)) * 100).quantize(Decimal("1")))


def to_hours(text) -> int | float:
    h = Decimal(re.sub(r"[^\d.]", "", str(text)))
    return int(h) if h == h.to_integral_value() else float(h)


def split_description(description: str) -> tuple[str, str]:
    """Our seed writes "counterparty | memo"; anything else is all counterparty."""
    counterparty, _, memo = (description or "").partition(" | ")
    return counterparty.strip(), memo.strip()


def nessie_row_to_transaction(raw: dict, source: str, profile_id: str) -> dict:
    """`source` is "deposit" or "purchase", the Nessie endpoint the row came from."""
    counterparty, memo = split_description(raw.get("description", ""))
    kind = source
    if source == "deposit" and counterparty.startswith(FAMILY_MARKER):
        kind = "transfer_in"
    return {
        "profileId": profile_id,
        "kind": kind,
        "amountCents": to_cents(raw["amount"]),
        "date": raw.get("transaction_date") or raw.get("purchase_date"),
        "counterparty": counterparty,
        "memo": memo,
        "nessieId": raw["_id"],
    }


def pct_of(cents: int, basis_points: int) -> int:
    return (cents * basis_points + 5000) // 10000


def check_paystub(stub: dict, rate_cents: int | None, federal_cents: int = 0) -> list[str]:
    """Code checks after extraction. A mismatch is a low-confidence warning, never a silent fix."""
    warnings = []
    gross = stub["grossCents"]
    if abs(stub["ssCents"] - pct_of(gross, SS_RATE_BP)) > 1 and stub["ssCents"] != 0:
        warnings.append(f"Social Security {stub['ssCents']} is not 6.2% of gross {gross}")
    if abs(stub["medicareCents"] - pct_of(gross, MEDICARE_RATE_BP)) > 1 and stub["medicareCents"] != 0:
        warnings.append(f"Medicare {stub['medicareCents']} is not 1.45% of gross {gross}")
    if rate_cents is not None:
        expected = int(Decimal(str(sum(stub["hoursByWeek"]))) * rate_cents)
        if expected != gross:
            warnings.append(f"hours x rate = {expected}, gross says {gross}")
    if gross - stub["ssCents"] - stub["medicareCents"] - federal_cents != stub["netCents"]:
        warnings.append("gross minus withholding does not equal net")
    return warnings


def find_paystub_deposit(stub: dict, transactions: list[dict]) -> dict | None:
    """The payroll deposit of exactly the net amount, 0 to 3 days after the period ends."""
    end = date.fromisoformat(stub["periodEnd"])
    for t in transactions:
        if t["kind"] != "deposit" or PAYROLL_MARKER not in t["counterparty"]:
            continue
        lag = (date.fromisoformat(t["date"]) - end).days
        if t["amountCents"] == stub["netCents"] and 0 <= lag <= DEPOSIT_WINDOW_DAYS:
            return t
    return None


def match_refund(txn: dict, cases: list[dict]) -> dict | None:
    """A payroll deposit within $1 of a case awaiting payroll's response is that case's refund."""
    if txn["kind"] != "deposit" or PAYROLL_MARKER not in txn["counterparty"]:
        return None
    for case in cases:
        if case["state"] != REFUND_PENDING_STATE:
            continue
        if abs(txn["amountCents"] - case["amountCents"]) <= REFUND_TOLERANCE_CENTS:
            return case
    return None
