"""Tax and status agent: runs the rules for a student and writes flags to Convex.

Runs when the Coordinator asks (Priya said "check my pay"), and on its own when the Ledger reports new
paystubs; then it tells the Coordinator what it found.

    .venv/bin/python -m agents.tax.agent
"""

import asyncio
import json
import os

from pathlib import Path

from uagents import Agent, Context

from agents.agentverse import add_mailbox_check
from agents.messages import (
    PORTS,
    FindingsReady, LocalFirstResolver, NewPaystub, RulesResult, RunRules, address_of,
)
from agents.messaging import heard, tell
from agents.tax import engine

agent = Agent(name="docket-tax", seed=os.environ["TAX_SEED"], port=PORTS["TAX"], mailbox=True,
              resolve=LocalFirstResolver(),
              description="Applies F-1 FICA, 20-hour and Form 8843 rules in code and argues the student's side in Docket's Hearing.",
              readme_path=str(Path(__file__).with_name("AGENTVERSE.md")),
              publish_agent_details=True)
add_mailbox_check(agent, "tax", PORTS["TAX"])


@agent.on_message(RunRules, replies=RulesResult)
async def run_rules(ctx: Context, sender: str, msg: RunRules):
    try:
        flags = await asyncio.to_thread(engine.run, msg.profile_id)
        await ctx.send(sender, RulesResult(flags_json=json.dumps(flags)))
    except Exception as e:
        ctx.logger.exception("rules run failed")
        await ctx.send(sender, RulesResult(flags_json="[]", error=str(e)))


@agent.on_message(NewPaystub)
async def on_new_paystubs(ctx: Context, sender: str, msg: NewPaystub):
    if sender != address_of("LEDGER"):
        return
    await heard("tax", sender, msg, f"{msg.count} new paystubs to check")
    try:
        flags = await asyncio.to_thread(engine.run, msg.profile_id)
    except Exception:
        ctx.logger.exception("rules run on new paystubs failed")
        return
    await tell(ctx, "tax", "COORDINATOR", FindingsReady(
        profile_id=msg.profile_id, paystub_count=msg.count, flags_json=json.dumps(flags)),
        f"{len(flags)} findings on {msg.count} new paystubs")


if __name__ == "__main__":
    agent.run()
