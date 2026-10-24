"""Caseworker agent: opens refund cases with a draft request and acts on the student's decision.

    .venv/bin/python -m agents.caseworker.agent
"""

import asyncio
import json
import os

from uagents import Agent, Context

from agents.caseworker import engine
from agents.messages import CaseDecision, CasesResult, DecisionResult, OpenCases, LocalFirstResolver, local_endpoint

agent = Agent(name="docket-caseworker", seed=os.environ["CASEWORKER_SEED"], port=8004,
              endpoint=local_endpoint("CASEWORKER"), resolve=LocalFirstResolver())


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
    except Exception as e:
        ctx.logger.exception("decision failed")
        await ctx.send(sender, DecisionResult(acted=False, error=str(e)))


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
