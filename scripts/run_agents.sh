#!/usr/bin/env bash
# Start every Docket agent from the repo root; Ctrl+C stops them all.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
trap 'kill 0' EXIT
$PY -m agents.tax.agent &
$PY -m agents.caseworker.agent &
sleep 2
$PY -m agents.coordinator.agent
