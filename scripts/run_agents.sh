#!/usr/bin/env bash
# Start every Docket agent (Ledger, Tax, Auditor, Caseworker, Coordinator) from the repo root; Ctrl+C stops them all.
# Prints each agent's address and Agentverse Inspector link first. Each agent also logs, about 20 seconds
# after it starts, whether its Agentverse mailbox is connected.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
echo "Docket agents:"
$PY -m scripts.print_agents --plain
echo
trap 'kill 0' EXIT
$PY -m agents.ledger.agent &
$PY -m agents.tax.agent &
$PY -m agents.auditor.agent &
$PY -m agents.caseworker.agent &
sleep 2
$PY -m agents.coordinator.agent
