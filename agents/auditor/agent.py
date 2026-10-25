"""Auditor agent: argues the employer's side of each finding in the Hearing, and issues the verdict in code.

    .venv/bin/python -m agents.auditor.agent

The objection checks and the verdict arrive in Step 6; this file gives the Auditor its identity,
its Agentverse readme, and the startup mailbox check.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from uagents import Agent

from agents.agentverse import add_mailbox_check
from agents.messages import PORTS, LocalFirstResolver, local_endpoint

load_dotenv()

# Swap this line for the Agentverse snippet (mailbox=True, readme, publish_agent_details) when you connect it.
agent = Agent(name="docket-auditor", seed=os.environ["AUDITOR_SEED"], port=PORTS["AUDITOR"],
              endpoint=local_endpoint("AUDITOR"), resolve=LocalFirstResolver())
README = Path(__file__).with_name("AGENTVERSE.md")
add_mailbox_check(agent, "auditor", PORTS["AUDITOR"])

if __name__ == "__main__":
    agent.run()
