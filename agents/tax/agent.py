"""Tax and status agent: runs the rules for a student when asked and writes flags to Convex.

    .venv/bin/python -m agents.tax.agent
"""

import asyncio
import json
import os

from uagents import Agent, Context

from agents.messages import RulesResult, RunRules, LocalFirstResolver, local_endpoint
from agents.tax import engine

agent = Agent(name="docket-tax", seed=os.environ["TAX_SEED"], port=8003, endpoint=local_endpoint("TAX"), resolve=LocalFirstResolver())


@agent.on_message(RunRules, replies=RulesResult)
async def run_rules(ctx: Context, sender: str, msg: RunRules):
    try:
        flags = await asyncio.to_thread(engine.run, msg.profile_id)
        await ctx.send(sender, RulesResult(flags_json=json.dumps(flags)))
    except Exception as e:
        ctx.logger.exception("rules run failed")
        await ctx.send(sender, RulesResult(flags_json="[]", error=str(e)))


if __name__ == "__main__":
    agent.run()
