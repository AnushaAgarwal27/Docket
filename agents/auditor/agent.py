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
from agents.messages import PORTS, LocalFirstResolver

load_dotenv()

agent = Agent(name="docket-auditor", seed=os.environ["AUDITOR_SEED"], port=PORTS["AUDITOR"], mailbox=True,
              resolve=LocalFirstResolver(),
              description="Argues the employer's side of every F-1 tax finding in Docket's Hearing; the verdict is decided in code.",
              readme_path=str(Path(__file__).with_name("AGENTVERSE.md")),
              publish_agent_details=True)
add_mailbox_check(agent, "auditor", PORTS["AUDITOR"])

if __name__ == "__main__":
    agent.run()
