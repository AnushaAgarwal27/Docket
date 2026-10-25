#!/usr/bin/env bash
# Start every Docket agent from the repo root; Ctrl+C stops them all.
#
#   Ledger      reads paystubs and the bank feed
#   Tax         runs the rules and argues the student's side
#   Auditor     argues the employer's side and issues the verdict
#   Caseworker  refund cases, approvals, payroll calls, letters
#   Researcher  Athena: answers what the file cannot and watches the rules that fired
#   Organizer   group cases across students at one employer
#   Filer       fills in the student's forms and submits what she approves
#   Coordinator the one the student talks to in ASI:One (started last, in the foreground)
#
# Prints each agent's address and Agentverse Inspector link first. Each agent also logs, about 20
# seconds after it starts, whether its Agentverse mailbox is connected.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python

# An agent with no seed cannot start, and its absence should be a readable message rather than a
# KeyError in the middle of the log.
for KEY in LEDGER TAX AUDITOR CASEWORKER RESEARCHER ORGANIZER FILER COORDINATOR; do
  if ! grep -qE "^${KEY}_SEED=.+" .env 2>/dev/null; then
    echo "Missing ${KEY}_SEED in .env. Run: $PY -m scripts.make_seeds" >&2
    exit 1
  fi
done

echo "Docket agents:"
$PY -m scripts.print_agents --plain
echo
trap 'kill 0' EXIT
$PY -m agents.ledger.agent &
$PY -m agents.tax.agent &
$PY -m agents.auditor.agent &
$PY -m agents.caseworker.agent &
$PY -m agents.researcher.agent &
$PY -m agents.organizer.agent &
$PY -m agents.filer.agent &
sleep 2
$PY -m agents.coordinator.agent
