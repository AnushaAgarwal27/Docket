"""Caseworker agent: opens refund cases with a draft request and acts on the student's decision.

    .venv/bin/python -m agents.caseworker.agent
"""

import asyncio
import json
import os

from pathlib import Path

from uagents import Agent, Context

from agents.caseworker import engine
from agents.agentverse import add_mailbox_check
from agents.messages import (
    PORTS, CaseDecision, CaseOpened, CasesResult, DecisionResult, LocalFirstResolver, OpenCases, RefundMatched,
    Verdict, WatchRefund, address_of,
)
from agents.messaging import heard, tell
from agents.store import dollars, log, mutation

agent = Agent(name="docket-caseworker", seed=os.environ["CASEWORKER_SEED"], port=PORTS["CASEWORKER"], mailbox=True,
              resolve=LocalFirstResolver(),
              description="Runs F-1 FICA refund cases from the student's approval to the refund deposit.",
              readme_path=str(Path(__file__).with_name("AGENTVERSE.md")),
              publish_agent_details=True)
add_mailbox_check(agent, "caseworker", PORTS["CASEWORKER"])


@agent.on_message(OpenCases, replies=CasesResult)
async def open_cases(ctx: Context, sender: str, msg: OpenCases):
    try:
        awaiting = await asyncio.to_thread(engine.open_refund_cases, msg.profile_id)
        await ctx.send(sender, CasesResult(awaiting_json=json.dumps(awaiting)))
    except Exception as e:
        ctx.logger.exception("opening cases failed")
        await ctx.send(sender, CasesResult(awaiting_json="[]", error=str(e)))


@agent.on_message(CaseDecision, replies=DecisionResult)
async def decide(ctx: Context, sender: str, msg: CaseDecision):
    try:
        pending = await asyncio.to_thread(engine.awaiting_approval, msg.profile_id)
        if not pending:
            await ctx.send(sender, DecisionResult(acted=False))
            return
        case = pending[0]
        await asyncio.to_thread(engine.approve if msg.approved else engine.decline, case)
        await ctx.send(sender, DecisionResult(acted=True, amount_cents=case["amountCents"]))
        if msg.approved:
            await tell(ctx, "caseworker", "LEDGER", WatchRefund(
                profile_id=msg.profile_id, case_id=case["_id"], amount_cents=case["amountCents"]),
                f"payroll asked for {dollars(case['amountCents'])}; watch for the refund", inputIds=[case["_id"]])
    except Exception as e:
        ctx.logger.exception("decision failed")
        await ctx.send(sender, DecisionResult(acted=False, error=str(e)))


@agent.on_message(Verdict)
async def on_verdict(ctx: Context, sender: str, msg: Verdict):
    """The Auditor's verdict decides whether a refund case opens on its own. Only an upheld refund
    finding does; anything else waits for the student's explicit OK, and the decision is logged."""
    if sender != address_of("AUDITOR"):
        return
    await heard("caseworker", sender, msg, f"{msg.rule_id}: {msg.verdict}", inputIds=[msg.hearing_id])
    if msg.rule_id != "FICA_EXEMPT_F1" or not msg.flag_id:
        return
    if msg.verdict != "upheld":
        await asyncio.to_thread(log, "caseworker", "case_not_opened",
                                f"Verdict {msg.verdict}: no case without the student's explicit OK ({msg.reason})",
                                inputIds=[msg.flag_id, msg.hearing_id])
        return
    try:
        awaiting = await asyncio.to_thread(engine.open_refund_cases, msg.profile_id)
    except Exception:
        ctx.logger.exception("opening the case after an upheld verdict failed")
        return
    case = next((c for c in awaiting if c["flagId"] == msg.flag_id), None)
    if case:
        await tell(ctx, "caseworker", "COORDINATOR", CaseOpened(
            profile_id=msg.profile_id, case_id=case["_id"], flag_id=msg.flag_id, amount_cents=case["amountCents"]),
            f"refund case for {dollars(case['amountCents'])} waiting for approval", inputIds=[case["_id"]])


@agent.on_message(RefundMatched)
async def on_refund(ctx: Context, sender: str, msg: RefundMatched):
    """The Ledger saw the refund in the bank: close the case, then tell the Coordinator."""
    if sender != address_of("LEDGER"):
        return
    await heard("caseworker", sender, msg, f"refund deposit for case {msg.case_id}", inputIds=[msg.transaction_id])
    try:
        await asyncio.to_thread(mutation, "cases:refundReceived",
                                {"caseId": msg.case_id, "transactionId": msg.transaction_id})
    except Exception as e:
        ctx.logger.exception("closing the case failed")
        await asyncio.to_thread(log, "caseworker", "refund_close_failed", str(e)[:200], inputIds=[msg.case_id])
        return
    await tell(ctx, "caseworker", "COORDINATOR", msg, f"case {msg.case_id} closed: refund received",
               inputIds=[msg.case_id])


@agent.on_interval(period=float(os.environ.get("CASEWORKER_POLL_SECONDS", "5")))
async def call_approved_cases(ctx: Context):
    """Approvals and follow-ups can come from the dashboard, which never messages this agent; pick those up
    here. Also writes the letter for any case that moved to written_request after a stall or refusal."""
    try:
        if await asyncio.to_thread(engine.prepare_pending_letters):
            ctx.logger.info("prepared written request(s) after a stall or refusal")
        if await asyncio.to_thread(engine.place_pending_calls):
            ctx.logger.info("placed payroll call(s) for approved cases")
    except Exception:
        ctx.logger.exception("placing pending calls failed")


if __name__ == "__main__":
    agent.run()
