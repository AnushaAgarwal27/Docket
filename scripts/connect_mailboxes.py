"""Connect every running Docket agent to its Agentverse mailbox, without the browser Inspector.

    .venv/bin/python -m scripts.connect_mailboxes

Does what the Inspector's Connect -> Mailbox button does: posts your Agentverse API key to each agent's
local /connect endpoint (built into uAgents), and the agent registers itself in Agentverse as a mailbox
agent. Needs the agents running (./scripts/run_agents.sh) and AGENTVERSE_API_KEY in .env (Agentverse:
profile menu -> API Keys). The key is only sent to the agents on 127.0.0.1 and from them to Agentverse;
it is never printed.
"""
import os
import sys

import requests
from dotenv import load_dotenv

from agents.agentverse import ROSTER
from agents.messages import PORTS

load_dotenv()


def main() -> int:
    token = os.environ.get("AGENTVERSE_API_KEY", "").strip()
    if not token:
        print("AGENTVERSE_API_KEY is not set in .env. Create one in Agentverse (profile menu -> API Keys).")
        return 1
    failed = 0
    for key, (name, _) in ROSTER.items():
        url = f"http://127.0.0.1:{PORTS[key]}/connect"
        try:
            r = requests.post(url, json={"user_token": token, "agent_type": "mailbox"}, timeout=60)
            body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        except requests.RequestException as e:
            print(f"{name:<19} not reachable on port {PORTS[key]} ({type(e).__name__}); is run_agents.sh running?")
            failed += 1
            continue
        ok = r.ok and body.get("success") is True
        failed += not ok
        print(f"{name:<19} {'connected' if ok else 'FAILED: ' + str(body.get('detail') or r.status_code)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
