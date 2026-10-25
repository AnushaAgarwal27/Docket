"""Tax and status agent: runs the rules for a student and writes flags to Convex.

Runs when the Coordinator asks (Priya said "check my pay"), and on its own when the Ledger reports new
paystubs; then it tells the Coordinator what it found.

    .venv/bin/python -m agents.tax.agent
"""

import asyncio
import json
import os

from uagents import Agent, Context

from agents.agentverse import add_mailbox_check
from agents.messages import (
    PORTS,
    FindingsReady, LocalFirstResolver, PaystubsRecorded, RulesResult, RunRules, address_of, local_endpoint,
)
from agents.tax import engine

agent = Agent(name="docket-tax", seed=os.environ["TAX_SEED"], port=8003, endpoint=local_endpoint("TAX"), resolve=LocalFirstResolver())
add_mailbox_check(agent, "tax", PORTS["TAX"])


@agent.on_message(RunRules, replies=RulesResult)
async def run_rules(ctx: Context, sender: str, msg: RunRules):
    try:
        flags = await asyncio.to_thread(engine.run, msg.profile_id)
        await ctx.send(sender, RulesResult(flags_json=json.dumps(flags)))
    except Exception as e:
        ctx.logger.exception("rules run failed")
        await ctx.send(sender, RulesResult(flags_json="[]", error=str(e)))


@agent.on_message(PaystubsRecorded)
async def on_new_paystubs(ctx: Context, sender: str, msg: PaystubsRecorded):
    if sender != address_of("LEDGER"):
        return
    try:
        flags = await asyncio.to_thread(engine.run, msg.profile_id)
    except Exception:
        ctx.logger.exception("rules run on new paystubs failed")
        return
    await ctx.send(address_of("COORDINATOR"), FindingsReady(
        profile_id=msg.profile_id, paystub_count=msg.count, flags_json=json.dumps(flags)))


if __name__ == "__main__":
    agent.run()
