"""Write docs/AGENTS.md: every Docket agent's name, role, port, address and Inspector link.

    .venv/bin/python -m scripts.print_agents          # writes docs/AGENTS.md
    .venv/bin/python -m scripts.print_agents --plain  # one line per agent, for run_agents.sh

Addresses are derived from the seeds in .env; the seeds themselves are never printed.
"""
import sys
from pathlib import Path

from agents.agentverse import ROSTER, inspector_url
from agents.messages import PORTS, address_of, configured

OUT = Path("docs/AGENTS.md")


def main() -> None:
    # An agent with no seed on this machine is simply not listed, so adding one to the roster never
    # breaks the script for someone who has not pulled the new seeds yet.
    rows = [(key, *ROSTER[key], PORTS[key], address_of(key)) for key in ROSTER if key in set(configured())]
    missing = [key for key in ROSTER if key not in set(configured())]
    if missing:
        print(f"note: no seed in .env for {', '.join(missing)}; run `python -m scripts.make_seeds`",
              file=sys.stderr)
    if "--plain" in sys.argv:
        for _, name, _, port, address in rows:
            print(f"{name:<19} {address}\n{'':<19} inspector: {inspector_url(address, port)}")
        return
    lines = [
        "# Docket agents",
        "",
        f"{len(rows)} Fetch.ai uAgents (uagents 0.26.1). Addresses come from each agent's seed in `.env`, so they stay",
        "the same as long as the seeds do. Regenerate this file with `python -m scripts.print_agents`.",
        "",
        "| Agent | Role | Port | Address | Inspector |",
        "|---|---|---|---|---|",
    ]
    for _, name, role, port, address in rows:
        lines.append(f"| {name} | {role} | {port} | `{address}` | [open]({inspector_url(address, port)}) |")
    lines += [
        "",
        "Each agent logs `Agentverse mailbox: connected` (or how to fix it) about 20 seconds after it starts.",
        "Agentverse profile URL for docket-coordinator: TODO paste from Agentverse (Agent Profile page).",
        "",
    ]
    OUT.write_text("\n".join(lines))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
