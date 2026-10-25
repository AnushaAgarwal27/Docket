"""Print the agent seeds this machine is missing, ready to paste into .env.

    .venv/bin/python -m scripts.make_seeds          # only the ones that are missing
    .venv/bin/python -m scripts.make_seeds --all    # every agent, for a fresh machine

A seed is what an agent's Agentverse address is derived from, so it must stay the same for the
life of the deployment: changing it gives the agent a new address and the student's chat, the
mailbox and anything pointing at the old address stop finding it. That is why this prints the
lines instead of editing .env itself.
"""
from __future__ import annotations

import argparse
import os
import secrets

from dotenv import load_dotenv

from agents.messages import PORTS

load_dotenv()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="print a seed for every agent, set or not")
    args = parser.parse_args()

    missing = [name for name in PORTS if args.all or not os.environ.get(f"{name}_SEED")]
    if not missing:
        print("Every agent already has a seed in .env. Nothing to add.")
        return
    print("# Add these to .env, then restart the agents (scripts/run_agents.sh).")
    print("# Keep them: an agent's address is derived from its seed.")
    for name in missing:
        print(f"{name}_SEED={secrets.token_hex(32)}")


if __name__ == "__main__":
    main()
