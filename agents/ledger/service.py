"""What the Ledger agent does on each tick. Every step logs to activity."""
from __future__ import annotations

from pathlib import Path

from agents.ledger.extract import transcribe_pdf, transcript_to_paystub
from agents.ledger.ledger import check_paystub, find_paystub_deposit, match_refund, nessie_row_to_transaction

AGENT = "ledger"


def sync_bank(store, nessie, account_id: str, profile_id: str) -> list[dict]:
    """Copy new Nessie rows into transactions. Returns the rows that were new."""
    new = []
    for source, rows in (("deposit", nessie.list_deposits(account_id)), ("purchase", nessie.list_purchases(account_id))):
        for raw in rows:
            txn = nessie_row_to_transaction(raw, source, profile_id)
            txn_id, created = store.upsert_transaction(txn)
            if created:
                new.append({**txn, "_id": txn_id})
    if new:
        store.log(AGENT, "recorded_transactions", f"{len(new)} new bank rows from Nessie",
                  output_ids=[t["_id"] for t in new])
    return new


def process_paystubs(store, profile_id: str, paystub_dir: Path, transcribe=transcribe_pdf,
                     done: set[str] | None = None) -> list[str]:
    """Transcribe PDFs not yet stored, check them in code, link each to its deposit.

    `done` remembers files already skipped or unreadable, so they are not sent to Claude every tick.
    """
    done = done if done is not None else set()
    stored = store.list_paystubs(profile_id)
    known = {p["sourceFile"] for p in stored}
    periods = {(p["employer"], p["periodStart"]) for p in stored}
    transactions = store.list_transactions(profile_id)
    created_ids = []
    for pdf in sorted(paystub_dir.glob("*.pdf")):
        if pdf.name in known or pdf.name in done:
            continue
        done.add(pdf.name)
        try:
            stub, rate, federal = transcript_to_paystub(transcribe(pdf), profile_id, pdf.name)
        except (RuntimeError, ValueError) as e:
            store.log(AGENT, "paystub_unreadable", f"{pdf.name}: {e}")
            continue
        if (stub["employer"], stub["periodStart"]) in periods:
            store.log(AGENT, "paystub_skipped", f"{pdf.name}: pay period {stub['periodStart']} is already recorded")
            continue
        warnings = check_paystub(stub, rate, federal)
        deposit = find_paystub_deposit(stub, transactions)
        if deposit is None:
            warnings.append("no matching payroll deposit within 3 days")
        stub_id, created = store.insert_paystub({**stub, "warnings": warnings or None,
                                                 "depositId": deposit["_id"] if deposit else None})
        if not created:
            continue
        created_ids.append(stub_id)
        periods.add((stub["employer"], stub["periodStart"]))
        detail = f"{pdf.name}: gross {stub['grossCents']}, SS {stub['ssCents']}, Medicare {stub['medicareCents']}"
        if warnings:
            detail += f"; low confidence: {'; '.join(warnings)}"
        store.log(AGENT, "recorded_paystub", detail, output_ids=[stub_id] + ([deposit["_id"]] if deposit else []))
    return created_ids


def match_refunds(store, profile_id: str, new_transactions: list[dict]) -> list[tuple[str, str]]:
    """Log the match, then hand it to the case state machine (cases:refundReceived closes it)."""
    matches = []
    cases = store.open_cases(profile_id)
    for txn in new_transactions:
        case = match_refund(txn, cases)
        if case is None:
            continue
        matches.append((case["_id"], txn["_id"]))
        store.log(AGENT, "refund_matched",
                  f"deposit {txn['amountCents']} from {txn['counterparty']} matches case amount {case['amountCents']}",
                  input_ids=[txn["_id"]], output_ids=[case["_id"]])
        store.refund_received(case["_id"], txn["_id"])
        cases = [c for c in cases if c["_id"] != case["_id"]]
    return matches
