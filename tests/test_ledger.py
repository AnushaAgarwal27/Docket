from pathlib import Path

import pytest

from agents.ledger.extract import PaystubTranscript, transcript_to_paystub
from agents.ledger.ledger import (check_paystub, find_paystub_deposit, match_refund,
                                  nessie_row_to_transaction, to_cents, to_hours)
from agents.ledger.service import match_refunds, process_paystubs, sync_bank
from seed import demo_data as d


class MemoryStore:
    """Same calls as ConvexLedgerStore in agents/ledger/agent.py, kept in memory."""

    def __init__(self):
        self.rows = {"transactions": {}, "paystubs": {}, "cases": {}, "activity": []}
        self.n = 0

    def _insert(self, table, doc):
        self.n += 1
        doc_id = f"{table}_{self.n}"
        self.rows[table][doc_id] = {"_id": doc_id, **doc}
        return doc_id

    def upsert_transaction(self, txn):
        for t in self.rows["transactions"].values():
            if t["nessieId"] == txn["nessieId"]:
                return t["_id"], False
        return self._insert("transactions", txn), True

    def list_transactions(self, profile_id):
        return [t for t in self.rows["transactions"].values() if t["profileId"] == profile_id]

    def list_paystubs(self, profile_id):
        return [p for p in self.rows["paystubs"].values() if p["profileId"] == profile_id]

    def insert_paystub(self, stub):
        return self._insert("paystubs", {k: v for k, v in stub.items() if v is not None}), True

    def open_cases(self, profile_id):
        return [c for c in self.rows["cases"].values() if c["profileId"] == profile_id]

    def refund_received(self, case_id, transaction_id):
        self.rows["cases"][case_id]["state"] = "closed"

    def log(self, agent, action, detail, input_ids=None, output_ids=None):
        self.rows["activity"].append({"agent": agent, "action": action, "detail": detail,
                                      "inputIds": input_ids, "outputIds": output_ids})

    def activity(self, agent=None):
        return [a for a in self.rows["activity"] if agent is None or a["agent"] == agent]


def test_money_parsing_is_exact():
    assert to_cents("$1,234.56") == 123456
    assert to_cents(664.92) == 66492  # float 664.92 * 100 = 66491.99999... in plain float math
    assert to_cents("$0.00") == 0
    with pytest.raises(ValueError):
        to_cents("about $40")


def test_hours_parsing():
    assert to_hours("24.00") == 24 and to_hours("7.50") == 7.5


def test_nessie_rows_become_transactions():
    dep = {"_id": "n1", "amount": 664.92, "transaction_date": "2026-01-26",
           "description": "University Dining Payroll | Payroll 2026-01-12 to 2026-01-25"}
    t = nessie_row_to_transaction(dep, "deposit", "p1")
    assert t == {"profileId": "p1", "kind": "deposit", "amountCents": 66492, "date": "2026-01-26",
                 "counterparty": "University Dining Payroll", "memo": "Payroll 2026-01-12 to 2026-01-25", "nessieId": "n1"}
    fam = {"_id": "n2", "amount": 609.01, "transaction_date": "2026-01-05", "description": "Family transfer - INR | INR 50000 at 82.10 INR/USD"}
    assert nessie_row_to_transaction(fam, "deposit", "p1")["kind"] == "transfer_in"
    buy = {"_id": "n3", "amount": 70.0, "purchase_date": "2026-01-10", "description": "Campus Furniture Outlet | furniture"}
    assert nessie_row_to_transaction(buy, "purchase", "p1")["date"] == "2026-01-10"


def test_clean_paystub_has_no_warnings():
    assert check_paystub(d.paystubs()[0], 1800) == []


def test_misread_number_becomes_warning_not_fix():
    stub = {**d.paystubs()[0], "ssCents": 4646}
    w = check_paystub(stub, 1800)
    assert any("Social Security" in x for x in w) and any("net" in x for x in w)
    assert stub["ssCents"] == 4646


def test_hours_times_rate_mismatch():
    assert any("hours x rate" in w for w in check_paystub(d.paystubs()[0], 1900))


def deposits_as_rows():
    return [{**t, "_id": f"t{i}"} for i, t in enumerate(d.payroll_deposits())]


def test_each_paystub_finds_its_deposit():
    rows = deposits_as_rows()
    for stub, dep in zip(d.paystubs(), rows):
        assert find_paystub_deposit(stub, rows)["_id"] == dep["_id"]


def test_refund_within_a_dollar_matches_case_awaiting_payroll_only():
    refund = {"_id": "r", "kind": "deposit", "amountCents": 44064, "counterparty": "University Dining Payroll"}
    cases = [{"_id": "c1", "state": "awaiting_response", "amountCents": 44000}]
    assert match_refund(refund, cases)["_id"] == "c1"
    assert match_refund(refund, [{**cases[0], "state": "closed"}]) is None
    assert match_refund(refund, [{**cases[0], "state": "awaiting_approval"}]) is None
    assert match_refund({**refund, "amountCents": 46000}, cases) is None
    assert match_refund({**refund, "counterparty": "Family transfer - INR"}, cases) is None


class FakeNessie:
    def __init__(self, deposits, purchases):
        self.d, self.p = deposits, purchases

    def list_deposits(self, account_id):
        return self.d

    def list_purchases(self, account_id):
        return self.p


def nessie_rows():
    deps, buys = [], []
    for i, t in enumerate(d.transactions()):
        row = {"_id": f"n{i}", "amount": t["amountCents"] / 100, "description": f"{t['counterparty']} | {t['memo']}"}
        if t["kind"] == "purchase":
            buys.append({**row, "purchase_date": t["date"]})
        else:
            deps.append({**row, "transaction_date": t["date"]})
    return deps, buys


def test_sync_bank_is_idempotent_and_logged():
    store = MemoryStore()
    nessie = FakeNessie(*nessie_rows())
    assert len(sync_bank(store, nessie, "acct", "p1")) == 30
    assert sync_bank(store, nessie, "acct", "p1") == []
    assert len(store.list_transactions("p1")) == 30
    assert [a["action"] for a in store.activity("ledger")] == ["recorded_transactions"]


def transcript_for(stub: dict) -> PaystubTranscript:
    """What Claude should copy off each PDF."""
    m = lambda c: f"${c // 100:,}.{c % 100:02d}"
    return PaystubTranscript(
        employer=stub["employer"], periodStart=stub["periodStart"], periodEnd=stub["periodEnd"],
        hoursByWeek=[f"{h}.00" for h in stub["hoursByWeek"]], hourlyRate="$18.00",
        grossPay=m(stub["grossCents"]), socialSecurityWithheld=m(stub["ssCents"]),
        medicareWithheld=m(stub["medicareCents"]), federalIncomeTaxWithheld="$0.00", netPay=m(stub["netCents"]))


def test_transcript_round_trips_to_demo_paystub():
    stub = d.paystubs()[4]
    row, rate, federal = transcript_to_paystub(transcript_for(stub), "p1", stub["sourceFile"])
    assert row == {"profileId": "p1", **stub} and rate == 1800 and federal == 0


def test_process_paystubs_links_deposits_and_skips_known(tmp_path: Path):
    store = MemoryStore()
    sync_bank(store, FakeNessie(*nessie_rows()), "acct", "p1")
    by_file = {s["sourceFile"]: s for s in d.paystubs()}
    for name in by_file:
        (tmp_path / name).write_bytes(b"%PDF-fake")
    calls = []

    def fake_transcribe(pdf):
        calls.append(pdf.name)
        return transcript_for(by_file[pdf.name])

    ids = process_paystubs(store, "p1", tmp_path, transcribe=fake_transcribe)
    assert len(ids) == 8
    stubs = store.list_paystubs("p1")
    assert all(s.get("depositId") and "warnings" not in s for s in stubs)
    assert sum(s["ssCents"] + s["medicareCents"] for s in stubs) == 44064
    assert process_paystubs(store, "p1", tmp_path, transcribe=fake_transcribe) == []
    assert len(calls) == 8  # known files are not sent to Claude again


def test_unreadable_paystub_is_logged(tmp_path: Path):
    store = MemoryStore()
    (tmp_path / "bad.pdf").write_bytes(b"%PDF")
    bad = transcript_for(d.paystubs()[0]).model_copy(update={"grossPay": "illegible"})
    assert process_paystubs(store, "p1", tmp_path, transcribe=lambda p: bad) == []
    assert store.activity("ledger")[0]["action"] == "paystub_unreadable"


def test_refund_match_logged_and_case_closed():
    store = MemoryStore()
    case_id = store._insert("cases", {"profileId": "p1", "state": "awaiting_response", "amountCents": 44064})
    refund = {"_id": "t9", "kind": "deposit", "amountCents": 44064, "counterparty": "University Dining Payroll"}
    assert match_refunds(store, "p1", [refund, {**refund, "_id": "t10"}]) == [(case_id, "t9")]
    assert store.activity("ledger")[0]["outputIds"] == [case_id]
    assert store.rows["cases"][case_id]["state"] == "closed"


def test_period_already_recorded_is_skipped_once(tmp_path: Path):
    """The anusha branch's seed:resetDemo writes the same 8 pay periods directly."""
    store = MemoryStore()
    stub = d.paystubs()[0]
    store.insert_paystub({**stub, "profileId": "p1", "sourceFile": "seed:paystub_01"})
    (tmp_path / stub["sourceFile"]).write_bytes(b"%PDF")
    done, calls = set(), []

    def transcribe(pdf):
        calls.append(pdf.name)
        return transcript_for(stub)

    assert process_paystubs(store, "p1", tmp_path, transcribe=transcribe, done=done) == []
    assert process_paystubs(store, "p1", tmp_path, transcribe=transcribe, done=done) == []
    assert calls == [stub["sourceFile"]]
    assert store.activity("ledger")[0]["action"] == "paystub_skipped"
