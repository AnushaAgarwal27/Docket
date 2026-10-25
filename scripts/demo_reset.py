"""One command to put the demo back to a clean, dialable state.

    .venv/bin/python -m scripts.demo_reset               # ready to call
    .venv/bin/python -m scripts.demo_reset --no-approve  # ready for her to say yes

Use --no-approve when the approval is the thing you are demonstrating: the Hearing game's live
case and ASI:One's review card each place the call themselves, and with the case already approved
there is nothing left for them to do, so the button looks broken.

Runs the whole chain in order, without needing the agents running:

    seed.reset        wipe Nessie and the demo tables, re-seed Priya and the simulated cohort
    Ledger            read seed/paystubs/*.pdf and the bank feed into the student file
    Tax               run the rules; write the flags with their own totals
    Caseworker        open the refund case with its draft request
    approve           move it to contacting_employer, the way the student's "yes" does

After this, `python -m scripts.call_now` places a real payroll call and the outcome will record.

The Ledger step is the slow one: each paystub is a Claude transcription, so a full reset takes a
few minutes. Nothing here is a shortcut — the same code the agents run, in the same order, so what
you rehearse against is what the demo does.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

from agents import store
from agents.caseworker import engine as caseworker
from agents.ledger.service import process_paystubs, sync_bank
from agents.store import dollars, mutation, query
from agents.tax import engine as tax
from seed.nessie import Nessie
from seed.reset import IDS_FILE

load_dotenv()

GREEN, RED, DIM, BOLD, OFF = "\033[32m", "\033[31m", "\033[2m", "\033[1m", "\033[0m"
PAYSTUB_DIR = Path(os.environ.get("PAYSTUB_DIR", "seed/paystubs"))


class LedgerStore:
    """The same adapter agents/ledger/agent.py uses, so ingestion behaves identically."""

    def upsert_transaction(self, txn):
        r = store.mutation("transactions:upsert", txn)
        return r["id"], r["created"]

    def list_transactions(self, profile_id):
        return store.query("transactions:listByProfile", {"profileId": profile_id})

    def list_paystubs(self, profile_id):
        return store.query("paystubs:listByProfile", {"profileId": profile_id})

    def insert_paystub(self, stub):
        return store.mutation("paystubs:record", {k: v for k, v in stub.items() if v is not None}), True

    def attach_paystub_pdf(self, pdf, paystub_id):
        from agents.convex_files import upload_and_attach
        upload_and_attach(pdf, "paystub", agent="ledger", paystubId=paystub_id)

    def open_cases(self, profile_id):
        return store.query("cases:listByProfile", {"profileId": profile_id})

    def refund_received(self, case_id, transaction_id):
        pass

    def log(self, agent, action, detail, input_ids=None, output_ids=None):
        extra = {k: v for k, v in (("inputIds", input_ids), ("outputIds", output_ids)) if v}
        store.log(agent, action, detail, **extra)


def step(n: int, what: str) -> None:
    print(f"\n{BOLD}{n}. {what}{OFF}")


def main() -> None:
    started = time.time()
    no_approve = "--no-approve" in sys.argv

    step(1, "Wiping and re-seeding")
    from seed import reset as seed_reset
    sys.argv = ["reset"]
    seed_reset.main()

    profile = next((p for p in query("profiles:list") if not p.get("simulated")), None)
    if profile is None:
        print(f"{RED}reset did not create a student file{OFF}")
        sys.exit(1)
    pid = profile["_id"]

    step(2, "Reading the bank feed and the paystub PDFs")
    print(f"   {DIM}each paystub is a Claude transcription; this is the slow part{OFF}")
    ledger = LedgerStore()
    if IDS_FILE.exists():
        import json
        ids = json.loads(IDS_FILE.read_text())
        account = ids.get("account") or ids.get("accountId")
        if account:
            sync_bank(ledger, Nessie(), account, pid)
    process_paystubs(ledger, pid, PAYSTUB_DIR)
    stubs = query("paystubs:listByProfile", {"profileId": pid})
    print(f"   {len(stubs)} paystubs on file")

    step(3, "Running the rules")
    for written in tax.run(pid):
        print(f"   {written['id']}")
    for flag in query("flags:listByProfile", {"profileId": pid}):
        if flag["ruleId"] == "FICA_EXEMPT_F1":
            # The Hearing sets this in the full flow; a call rehearsal only needs the case to open.
            if flag["status"] != "open":
                mutation("flags:setStatus", {"flagId": flag["_id"], "status": "open"})
            print(f"   {flag['ruleId']}: {dollars(flag['amountCents'])} "
                  f"across {len(flag.get('paystubIds') or [])} paystubs")

    step(4, "Opening the refund case")
    cases = caseworker.open_refund_cases(pid)
    if not cases:
        print(f"{RED}   no case opened — the FICA rule may not have fired{OFF}")
        sys.exit(1)
    case = cases[0]
    print(f"   {case['_id']}  {dollars(case['amountCents'])}")

    if no_approve:
        # Leave the case where the student's "yes" is still to come. The Hearing game's live case
        # and the review card in ASI:One both do their own approving, and neither has anything to
        # approve if this script already did it -- which looks exactly like a broken button.
        print(f"\n{GREEN}Ready in {time.time() - started:.0f}s.{OFF} The case is waiting for her yes.")
        print(f"   state: {query('cases:get', {'caseId': case['_id']})['state']}")
        print("\nApprove it from whichever surface you are showing:")
        print("  the Hearing game   http://localhost:5173/game.html  -> the Live case -> Approve the call")
        print("  ASI:One            say \"yes, contact payroll\" to docket-coordinator")
        print("  the dashboard      the Approve button on the case")
        print(f"\n{DIM}Either way the Caseworker places the real call within ~5s.{OFF}\n")
        return

    step(5, "Approving it, the way the student's yes does")
    mutation("cases:approve", {"caseId": case["_id"]})
    print(f"   state: {query('cases:get', {'caseId': case['_id']})['state']}")

    print(f"\n{GREEN}Ready in {time.time() - started:.0f}s.{OFF} Place the call:")
    print(f"  .venv/bin/python -m scripts.call_now")
    print(f"\n{DIM}Then check it recorded:  .venv/bin/python -m scripts.demo_ready{OFF}\n")


if __name__ == "__main__":
    main()
