"""Ledger agent: bank rows from Nessie and paystubs from PDFs into the shared file.

    .venv/bin/python -m agents.ledger.agent

Needs LEDGER_SEED, CONVEX_URL and ANTHROPIC_API_KEY in .env. With NESSIE_API_KEY and either
NESSIE_ACCOUNT_ID or the .nessie_ids.json written by `python -m seed.reset`, it also syncs the bank;
without it, it only reads paystubs.
Uses agents/store.py and the paystubs/cases Convex functions from the anusha branch.
"""
import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from uagents import Agent, Context

from agents import store
from agents.messaging import heard, tell
from agents.convex_files import upload_and_attach
from agents.agentverse import add_mailbox_check
from agents.chat import add_chat, no_student, student
from agents.messages import PORTS, LocalFirstResolver, NewPaystub, RefundMatched, WatchRefund
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

    def attach_paystub_pdf(self, pdf: Path, paystub_id: str) -> None:
        upload_and_attach(pdf, "paystub", agent="ledger", paystubId=paystub_id)

    def open_cases(self, profile_id: str) -> list[dict]:
        return store.query("cases:listByProfile", {"profileId": profile_id})

    def refund_received(self, case_id: str, transaction_id: str) -> None:
        # The Caseworker owns the case: the tick sends it RefundMatched, and it closes the case.
        pass

    def log(self, agent, action, detail, input_ids=None, output_ids=None) -> None:
        extra = {k: v for k, v in (("inputIds", input_ids), ("outputIds", output_ids)) if v}
        store.log(agent, action, detail, **extra)


agent = Agent(name="docket-ledger", seed=os.environ["LEDGER_SEED"], port=PORTS["LEDGER"], mailbox=True,
              resolve=LocalFirstResolver(),
              description="Reads F-1 students' paystub PDFs and bank deposits into one checked record for Docket.",
              readme_path=str(Path(__file__).with_name("AGENTVERSE.md")),
              publish_agent_details=True)
add_mailbox_check(agent, "ledger", PORTS["LEDGER"])
ledger_store = ConvexLedgerStore()
nessie = Nessie() if os.environ.get("NESSIE_API_KEY") else None
done_files: set[str] = set()
last_profile: dict[str, str | None] = {"id": None}


def account_id() -> str:
    return os.environ.get("NESSIE_ACCOUNT_ID") or json.loads(IDS_FILE.read_text())["accountId"]


def profile_id() -> str | None:
    match = [p for p in store.query("profiles:list") if p["name"] == PROFILE_NAME]
    return match[0]["_id"] if match else None


@agent.on_interval(period=POLL_SECONDS)
async def tick(ctx: Context):
    # Every call in this tick is blocking I/O, and process_paystubs is the slowest thing the agent
    # does: one Claude transcription per PDF, tens of seconds for a full reset. Run directly, it
    # holds the event loop the whole time, and an agent that cannot reach its own event loop cannot
    # answer anything -- not a message from the Tax agent, and not the /connect request that creates
    # its Agentverse mailbox, which is how this surfaced: the Ledger was the one agent whose mailbox
    # would not connect, and it looked like a network problem rather than a blocked loop.
    pid = await asyncio.to_thread(profile_id)
    if pid is None:
        ctx.logger.info(f"no profile named {PROFILE_NAME}; run python -m seed.reset")
        return
    new_txns = await asyncio.to_thread(
        sync_bank, ledger_store, nessie, account_id(), pid) if nessie else []
    if pid != last_profile["id"]:
        done_files.clear()  # a reset made a new student file, so read every PDF again
        last_profile["id"] = pid
    new_stubs = await asyncio.to_thread(
        process_paystubs, ledger_store, pid, PAYSTUB_DIR, done=done_files)
    if await asyncio.to_thread(store.query, "profiles:get", {"profileId": pid}) is None:
        return  # reset while this tick ran; the next tick starts over with the new profile
    if new_stubs:
        # Tax checks them right away, before Priya asks.
        await tell(ctx, "ledger", "TAX", NewPaystub(profile_id=pid, count=len(new_stubs)),
                   f"{len(new_stubs)} new paystubs recorded", inputIds=new_stubs)
    matches = await asyncio.to_thread(match_refunds, ledger_store, pid, new_txns)
    for case_id, txn_id in matches:
        # The Caseworker closes the case and tells the Coordinator, who tells Priya.
        case = await asyncio.to_thread(store.query, "cases:get", {"caseId": case_id})
        txn = next(t for t in new_txns if t["_id"] == txn_id)
        await tell(ctx, "ledger", "CASEWORKER", RefundMatched(
            profile_id=pid, case_id=case_id, transaction_id=txn_id, amount_cents=case["amountCents"],
            counterparty=txn["counterparty"]), f"deposit of {store.dollars(txn['amountCents'])} matches case {case_id}",
            inputIds=[txn_id, case_id])
        watching = ctx.storage.get("watching") or {}
        watching.pop(case_id, None)
        ctx.storage.set("watching", watching)
    if new_txns or new_stubs or matches:
        ctx.logger.info(f"{len(new_txns)} transactions, {len(new_stubs)} paystubs, {len(matches)} refunds matched")


@agent.on_message(WatchRefund)
async def on_watch(ctx: Context, sender: str, msg: WatchRefund):
    """The Caseworker asked payroll for a refund; remember to look for it in the bank feed."""
    await heard("ledger", sender, msg, f"watch for a {store.dollars(msg.amount_cents)} refund (case {msg.case_id})",
                inputIds=[msg.case_id])
    watching = ctx.storage.get("watching") or {}
    watching[msg.case_id] = msg.amount_cents
    ctx.storage.set("watching", watching)


# --- ASI:One ------------------------------------------------------------------
# What this agent read out of the bank and the paystub PDFs. Numbers come from the rows it wrote.
def answer(question: str) -> str:
    from agents.store import dollars, query
    p = student()
    if p is None:
        return no_student()
    stubs = query("paystubs:listByProfile", {"profileId": p["_id"]})
    txns = query("transactions:listByProfile", {"profileId": p["_id"]})
    if not stubs and not txns:
        return "I haven't read anything yet. No paystubs on file and no bank rows synced."
    gross = sum(s.get("grossCents") or 0 for s in stubs)
    fica = sum((s.get("ssCents") or 0) + (s.get("medicareCents") or 0) for s in stubs)
    linked = sum(1 for s in stubs if s.get("depositId"))
    employers = sorted({s.get("employer", "") for s in stubs if s.get("employer")})
    return (
        f"I'm Docket's Ledger. I read the bank feed and the paystub PDFs, and every number below is "
        f"one I wrote into the student file.\n\n"
        f"- **{len(stubs)} paystubs** from {', '.join(employers) or 'an unnamed employer'}\n"
        f"- **{dollars(gross)}** gross across them\n"
        f"- **{dollars(fica)}** withheld as Social Security and Medicare\n"
        f"- **{linked} of {len(stubs)}** matched to a bank deposit of exactly their net pay\n"
        f"- **{len(txns)} bank rows** synced from the account\n\n"
        f"Claude transcribes what each paystub prints; the arithmetic and the matching are done in "
        f"code. Whether that withholding is owed is the Tax agent's call, not mine."
    )


add_chat(agent, "ledger", answer)


if __name__ == "__main__":
    agent.run()
