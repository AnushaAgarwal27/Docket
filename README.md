# Docket

A caseworker for F-1 students: finds money and deadlines they didn't know about, proves every
rule with the exact official clause, and follows up until the problem is fixed.

Built at Cal Hacks 13.0. The full build plan is in `docs/`.

## Layout

| Path | What | Owner |
|---|---|---|
| `convex/` | Shared student file (schema + functions) | Person 3 |
| `agents/coordinator` | ASI:One chat, routing, approvals | Person 1 |
| `agents/ledger` | Nessie polling, paystub extraction, refund matching | Person 2 |
| `agents/tax` | Runs rules, writes flags | Person 2 |
| `agents/caseworker` | Case state machine, Cartesia call | Person 1 + 3 |
| `agents/price` | Apify prices, budget | Person 3 |
| `rules/` | `rules.yaml`, `rules.py`, quote checker | Person 2 |
| `seed/` | Nessie + Convex seed and reset, paystub PDFs | Person 2 |
| `eval/` | 25 profiles + plain Claude vs Docket runner | Person 1 + 2 |
| `dashboard/` | Live dashboard | Person 3 |

## Setup

Python 3.12 (uAgents does not support 3.14):

    python3.12 -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env   # fill in keys

## Rules we never break

- Code does all math, counting and decisions. Claude transcribes and explains.
- No rule is shown without a quote that matches the stored source word for word.
- The call agent says it is an AI and that the call may be recorded. It never pretends to be the student.
- Nothing is sent or called without the student's approval.
- Synthetic data only.
- Every flag says "likely" and points to the school's international office. Not tax or immigration advice.

## Sponsor tools

<!-- One section per sponsor: exactly what the tool does in the product. -->
