# Data and rules layer (Person 2)

Priya's synthetic demo data, the Nessie seed and reset, the paystub PDFs, the rules engine and the quote checker. Python 3.12 or 3.13 (uAgents does not support 3.14).

```bash
python -m pytest -q                       # 29 tests, no network
python -m seed.make_paystub_pdfs       # 8 PDFs into seed/paystubs/
python -m seed.reset --dry-run         # print the Nessie seed
NESSIE_API_KEY=... python -m seed.reset             # wipe and re-seed Nessie
NESSIE_API_KEY=... python -m seed.release_refund 2026-11-07   # "simulate 2 weeks"
python -m rules.verify_sources          # check every rule quote against sources/*.txt
```

## What's here

| File | What it does |
|---|---|
| `seed/demo_data.py` | Priya's profile, school calendar, 8 paystubs, 30 transactions, hidden refund. One source of truth. |
| `rules/rules.yaml` | The three rules, each with source URL, quote and action. |
| `rules/rules.py` | `fica_exempt`, `over_20_hours_in_session`, `needs_8843`. Pure functions, integer cents. |
| `rules/quote_checker.py` | Normalizes whitespace, quotes and dashes, then requires an exact, case-sensitive match of at least 8 words. |
| `rules/engine.py` | Runs the rules, checks the quotes, returns flags plus one activity row per rule (raised, not triggered or rejected). |
| `seed/nessie.py` | Nessie client, `seed_priya`, `release_refund`. |

## Demo numbers (all tested)

8 biweekly stubs from 2026-01-12, 40 h at $18: gross $720.00, Social Security $44.64, Medicare $10.44, net $664.92. Withheld in error: **$440.64**. Paystub 5 splits 16 + 24, so the week of 2026-03-16 trips the 20-hour flag. Priya has 8843s recorded for 2024 and 2025, so her run gives exactly two flags.

## Before the demo

1. **Quotes.** `rules/rules.yaml` now uses the verified quotes from the anusha branch (IRS Pub 519, 8 CFR 214.2(f)(9)(i) on eCFR, IRS About Form 8843). `seed.fetch_sources` on that branch stores the pages and checks each quote.
2. **Nessie endpoints** follow the public docs from memory. Check them against the Nessie documentation before the first real seed.

## For the rest of the team

- **Person 3 (Convex):** `seed/reset.py` calls a Convex mutation `admin:reset` when `CONVEX_URL` is set.
- **Person 1 (agents):** `rules.engine.evaluate(...)` is what the Tax agent calls. Pass Claude's returned clause through `quotes={rule_id: clause}` so it goes through the same check. A fabricated clause comes back as a `flag_rejected` activity row, which is the demo rejection.

## Rule decisions worth knowing

- Calendar years: any part of a year counts, so arrival in August 2024 makes 2026 year 3. FICA exemption is F-1 only for now.
- 20-hour limit: a week counts as in session if its start date falls inside a session in the school calendar. Exactly 20 is fine.
- 8843: required while the student is in exempt years 1 to 5. Due April 15 with US wages that year, otherwise June 15. Weekend shifts are not applied.

## Ledger agent

Built on the anusha branch's `agents/store.py` and Convex functions (`paystubs:*`, `cases:*`, `profiles:list`, `activity:log`), so it runs once that branch is merged. This branch adds `convex/transactions.ts`.

| File | What it does |
|---|---|
| `agents/ledger/ledger.py` | Nessie row parsing, code checks (6.2%, 1.45%, hours x rate, net), deposit linking (exact net, 0 to 3 days), refund matching (within $1, payroll, case in `awaiting_response`). |
| `agents/ledger/extract.py` | Claude copies each paystub's printed values as text; code parses every number. |
| `agents/ledger/service.py` | Sync Nessie, transcribe new PDFs, skip pay periods already recorded, hand refund matches to `cases:refundReceived`. One activity row per action. |
| `agents/ledger/agent.py` | Runs the three steps every 30 s. |

```bash
python -m seed.make_paystub_pdfs    # 8 PDFs into seed/paystubs/
python -m seed.reset                # Nessie seed + seed:resetDemo
python -m agents.ledger.agent
```

`seed:resetDemo` still writes the 8 paystubs directly, so until it stops doing that the Ledger logs those periods as already recorded and only adds the bank rows and deposit matches.
