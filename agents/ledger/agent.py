"""Ledger agent: bank rows from Nessie and paystubs from PDFs into the shared file.

    .venv/bin/python -m agents.ledger.agent

Needs LEDGER_SEED, CONVEX_URL and ANTHROPIC_API_KEY in .env. With NESSIE_API_KEY and either
NESSIE_ACCOUNT_ID or the .nessie_ids.json written by `python -m seed.reset`, it also syncs the bank;
without it, it only reads paystubs.
Uses agents/store.py and the paystubs/cases Convex functions from the anusha branch.
"""
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from uagents import Agent, Context

from agents import store
from agents.messages import LocalFirstResolver, RefundLanded, address_of, local_endpoint
from agents.ledger.service import match_refunds, process_paystubs, sync_bank
from seed.nessie import Nessie
from seed.reset import IDS_FILE

load_dotenv()

PROFILE_NAME = os.environ.get("DEMO_PROFILE_NAME", "Priya Sharma")
PAYSTUB_DIR = Path(os.environ.get("PAYSTUB_DIR", "seed/paystubs"))
POLL_SECONDS = float(os.environ.get("LEDGER_POLL_SECONDS", "30"))


class ConvexLedgerStore:
    """The few shared-file calls the Ledger needs, on top of agents/store.py."""

    def upsert_transaction(self, txn: dict) -> tuple[str, bool]:
        r = store.mutation("transactions:upsert", txn)
        return r["id"], r["created"]

    def list_transactions(self, profile_id: str) -> list[dict]:
        return store.query("transactions:listByProfile", {"profileId": profile_id})

    def list_paystubs(self, profile_id: str) -> list[dict]:
        return store.query("paystubs:listByProfile", {"profileId": profile_id})

    def insert_paystub(self, stub: dict) -> tuple[str, bool]:
        return store.mutation("paystubs:record", {k: v for k, v in stub.items() if v is not None}), True

    def open_cases(self, profile_id: str) -> list[dict]:
        return store.query("cases:listByProfile", {"profileId": profile_id})

    def refund_received(self, case_id: str, transaction_id: str) -> None:
        store.mutation("cases:refundReceived", {"caseId": case_id, "transactionId": transaction_id})

    def log(self, agent, action, detail, input_ids=None, output_ids=None) -> None:
        extra = {k: v for k, v in (("inputIds", input_ids), ("outputIds", output_ids)) if v}
        store.log(agent, action, detail, **extra)


agent = Agent(name="docket-ledger", seed=os.environ["LEDGER_SEED"], port=8002,
              endpoint=local_endpoint("LEDGER"), resolve=LocalFirstResolver())
ledger_store = ConvexLedgerStore()
nessie = Nessie() if os.environ.get("NESSIE_API_KEY") else None
done_files: set[str] = set()


def account_id() -> str:
    return os.environ.get("NESSIE_ACCOUNT_ID") or json.loads(IDS_FILE.read_text())["accountId"]


def profile_id() -> str | None:
    match = [p for p in store.query("profiles:list") if p["name"] == PROFILE_NAME]
    return match[0]["_id"] if match else None


@agent.on_interval(period=POLL_SECONDS)
async def tick(ctx: Context):
    pid = profile_id()
    if pid is None:
        ctx.logger.info(f"no profile named {PROFILE_NAME}; run python -m seed.reset")
        return
    new_txns = sync_bank(ledger_store, nessie, account_id(), pid) if nessie else []
    new_stubs = process_paystubs(ledger_store, pid, PAYSTUB_DIR, done=done_files)
    matches = match_refunds(ledger_store, pid, new_txns)
    for case_id, txn_id in matches:
        # Tell the Coordinator, so Priya hears about her refund without asking.
        case = store.query("cases:get", {"caseId": case_id})
        txn = next(t for t in new_txns if t["_id"] == txn_id)
        await ctx.send(address_of("COORDINATOR"), RefundLanded(
            profile_id=pid, case_id=case_id, amount_cents=case["amountCents"], counterparty=txn["counterparty"]))
    if new_txns or new_stubs or matches:
        ctx.logger.info(f"{len(new_txns)} transactions, {len(new_stubs)} paystubs, {len(matches)} refunds matched")


if __name__ == "__main__":
    agent.run()
