# Docket

**A caseworker for F-1 students.** Docket finds money and deadlines students don't know about, proves every rule with the exact official clause, and follows up until the problem is fixed.

> Ask Claude and you get a confident answer. Ask Docket and you get the right one, with the clause that proves it, and we follow up until the money is back.

Built at Cal Hacks 13.0.

---

## The problem

International students arrive with no idea how US pay, taxes, and prices work.

- Most F-1 students are **exempt from Social Security and Medicare tax for their first 5 calendar years**, yet employers often withhold it anyway.
- **Every F-1 student must file Form 8843 every year**, even with no income.
- **On-campus work is capped at 20 hours a week** while school is in session.

Students rarely know any of this, so they can't even ask the right question.

**Scope (non-negotiable):** we are not an orientation app. We own the *money side* of F-1 status, meaning anything where a mistake costs money or puts status at risk. Every feature must read from or write to the shared student file, or it doesn't get built.

## What a prompt can't do, and Docket does

| | |
|---|---|
| **Notice** | Reads paystubs and flags problems the student never knew to ask about. |
| **Prove** | Every flag shows the exact clause from an official source, checked word for word in code. |
| **Act** | Drafts the request, calls payroll (with approval), prepares the forms. |
| **Remember** | Keeps a case open for weeks, with a call log and follow-up dates. |

## The hero chain (the whole demo hangs on this)

1. A new paystub lands. The **Ledger** agent records it.
2. The **Tax and status** agent sees Social Security and Medicare withheld, counts Priya's calendar years *in code* (year 3, so exempt), and flags it with the IRS clause. It also sees 24 hours worked in one week and flags the 20-hour limit.
3. The **Caseworker** opens a refund case. Priya approves in ASI:One. Cartesia calls payroll, and the call is logged.
4. A refund deposit appears in the bank. The Ledger matches it to the case, and the Caseworker closes it.

No agent tells another what to do. Each one reacts to what the others wrote in the shared file.

**Demo persona:** Priya Sharma, F-1, from Pune, India. Arrived August 2024. CS sophomore. On-campus job at dining services, $18/hour. Her parents send rupees for rent.

## Architecture

```
                 Priya (ASI:One)  <──>  Coordinator agent
                                           │ routes work, asks approval
         ┌──────────────┬──────────────────┼──────────────┐
      Ledger         Tax & status      Caseworker       Price
   Nessie bank,     rules run in      cases, approvals,  Apify prices,
   paystubs,        code; clause      Cartesia calls     budget from
   Claude reads     checked in code   payroll            ledger
         └──────────────┴────────┬─────────┴──────────────┘
                 Shared student file on Convex
   profiles · transactions · paystubs · sources · flags · cases · calls · activity
                                 │
                          Live dashboard
                  (activity feed, cases, money)
```

- 5 agents, each a **Fetch.ai uAgent** in Python 3.12/3.13. Only the Coordinator speaks the chat protocol to ASI:One.
- **Convex** is the shared student file. The dashboard shows every row the moment it lands.
- **Nessie** feeds the Ledger, **Apify** fetches official sources and prices, and **Cartesia** makes the calls.

### The shared file ([`convex/schema.ts`](convex/schema.ts))

| Table | Holds | Written by | Read by |
|---|---|---|---|
| `profiles` | Visa, arrival date, school, home country/currency, work auth, masked phone | Coordinator | Every agent |
| `transactions` | Every Nessie deposit, purchase, and transfer | Ledger | Tax, Price, Caseworker, dashboard |
| `paystubs` | Period, gross, hours by week, SS/Medicare withheld, net, employer | Ledger | Tax, dashboard |
| `sources` | Official page URL, fetched text, fetch time, content hash | Apify collector | Tax, quote checker |
| `flags` | Rule id, amount, explanation, quoted clause, source id, status | Tax | Caseworker, dashboard |
| `cases` | Flag id, state, amount owed, deadlines, next follow-up, outcome | Caseworker | Ledger, dashboard |
| `calls` | Who answered, summary, promised date, reference no., transcript | Caseworker (Cartesia webhook) | Caseworker, dashboard |
| `activity` | Agent, action, inputs/outputs, source id, timestamp | **Every agent, every action** | Dashboard feed |

**The one rule for `activity`:** every agent writes one row for every action it takes, *including actions it decided not to take*. The dashboard feed is just this table, newest first.

Money is stored in **integer cents everywhere**. No floats, and no numbers written by the model.

## The agents

**1. Coordinator** is the only agent Priya talks to. It's a uAgent with a mailbox and the chat protocol, reachable in ASI:One. It handles intents like "check my pay", "what's wrong?", "yes, contact payroll", "is $70 normal for a table?", and "explain in Hindi". It sends approval prompts (an interactive card if we find Fetch's format), and its echo guard ignores ASI:One replaying our own replies.

**2. Ledger** turns bank data and paystubs into clean rows.
- It polls Nessie every 30s, using the Nessie id for dedupe.
- Claude *transcribes* paystubs into a fixed JSON shape but never calculates.
- Code then checks that SS ≈ 6.2% of gross, Medicare ≈ 1.45%, hours × rate = gross, and net matches a deposit within 3 days. A mismatch becomes a warning, never a silent fix.
- Refund matching: a deposit within $1 of an open case, from the employer, closes the loop.

**3. Tax and status** applies rules to Priya's facts. Rules run in code. Claude only turns a rule hit into one plain-English sentence (optionally in Hindi) and must return the clause it relied on.

**4. Caseworker** turns flags into cases and pushes them to a result.
- States: `open → awaiting_approval → contacting_employer → awaiting_response → refund_received → closed`. A refusal from payroll goes to `escalate_irs`, which produces a Forms 843 + 8316 checklist.
- It drafts the request first and shows it to Priya.
- The call goes through a Cartesia Managed Agent with two webhook tools: `get_case_summary` and `log_call_outcome`. The agent says it's an AI calling with Priya's permission and that the call may be recorded, and it never pretends to be Priya.
- Follow-ups are a Convex scheduled function. A "simulate 2 weeks" button jumps the clock for the demo.

**5. Price** (should-have) answers "is this normal, and can I afford it?" Apify gives price ranges and the ledger gives the budget. For family transfers it also computes the INR markup against the market rate.

## Rules engine and source verification

This is our answer to "isn't this just Claude?" **The model can explain a rule but can never create one.**

1. **Collect sources:** Apify fetches the exact text of IRS Pub 519 (NRA students, SS/Medicare), the Form 843 and 8316 instructions, the Form 8843 page, and the official on-campus employment rule into `sources`, with a hash.
2. **[`rules/rules.yaml`](rules/rules.yaml):** each rule names its check function, source URL, exact quote, and action.
3. **[`rules/rules.py`](rules/rules.py):** each check is a pure function:
   - `fica_exempt`: F-1, calendar year ≤ 5 counted from arrival, SS/Medicare withheld. Returns the total in cents.
   - `over_20_hours_in_session`: any week above 20 hours while school is in session.
   - `needs_8843`: F-1/J-1 with no 8843 recorded for last year. Returns the deadline.
4. **Quote checker:** code normalizes whitespace and checks that Claude's quote appears *exactly* in the stored source. If it doesn't match, the flag isn't shown and an `activity` row records the rejection. We show one rejection in the demo.
5. **Honest labels:** every flag says "likely" and ends with "Confirm with your school's international office."

## Demo data (all synthetic)

8 biweekly paystubs from University Dining Services, Spring 2026, each 40 hours at $18/hour:

| Field | Each paystub | Total over 8 |
|---|---|---|
| Gross | $720.00 | $5,760.00 |
| Social Security (6.2%) | $44.64 | $357.12 |
| Medicare (1.45%) | $10.44 | $83.52 |
| Net | $664.92 | $5,319.36 |

**Withheld in error: $440.64**, the hero number. Paystub 5 splits its 40 hours as 16 + 24, so the 24-hour week triggers the 20-hour flag without changing any totals.

**Nessie seed:**
- 1 customer and 1 checking account.
- 8 payroll deposits of $664.92.
- About 20 purchases (groceries, a $70 table, phone, rent).
- 2 family transfers in INR with the rate in the memo.
- The $440.64 "FICA refund" deposit, which is *created* when someone clicks "simulate 2 weeks."

**Reset script:** one command wipes Convex and Nessie and re-seeds everything. Run it before every rehearsal.

## Evaluation: plain Claude vs Docket

We use 25 synthetic profiles with known answers:

| Count | Case | Expected |
|---|---|---|
| 8 | Exempt students with SS wrongly withheld | Flag |
| 4 | Students in their 6th calendar year or later | **No flag** (where models slip) |
| 4 | Clean paystubs, nothing withheld | No flag |
| 5 | A week over 20 hours, one of them during winter break | Flag, except the break week |
| 4 | No income at all | Form 8843 reminder |

Both versions run on every profile:
- **Plain Claude:** the profile plus "Is anything wrong with this student's pay or filings?" with no tools and no sources.
- **Docket:** the full pipeline.

We score correct flags, false flags, and whether each flag cites a real clause. The misses go in this README too.

## Team split

| Person | Owns | Sponsor tools |
|---|---|---|
| **Person 1: Agents** | Coordinator, agent wiring, Caseworker state machine, ASI:One approvals, eval runner | Fetch.ai, Anthropic |
| **Person 2: Data and rules** | Ledger, Nessie seed and reset, paystub PDFs and extraction, sources, rules engine, quote checker, 25 test profiles | Nessie, Apify, Claude |
| **Person 3: Experience** | Convex schema and functions, live dashboard, Cartesia call, Hindi explanations, Price agent, video | Convex, Cartesia, Apify |

**Everyone:** interview at least 2 F-1 students at the event for a real quote, and write the README section for your own sponsor tools.

## Timeline and gates

| When | Phase | Gate |
|---|---|---|
| Now → Sat 3 PM | Foundations: Coordinator in ASI:One, Nessie seed, paystubs, sources, Convex schema, dashboard shell, Cartesia talking | **Gate 1:** one paystub becomes a flag on the live dashboard |
| Sat 3 PM → 10 PM | Hero chain: Caseworker states, approval, Tax agent, quote checker, Cartesia call + webhook, refund match | **Gate 2:** hero chain runs end to end once; Devpost draft in |
| Sat 10 PM → Sun 2 AM | Harden: eval runner, 25 profiles, reset script, Price agent, Hindi, Agentverse badges | **Gate 3:** three clean runs in a row after a reset |
| Sun 2 → 5:30 AM | Polish, rehearse the pitch twice | **Feature freeze 5:30 AM** |
| Sun 5:30 → 8:30 AM | Record the video, submit on Devpost by 8:30 (hard deadline 9:00) | |

If we miss a gate by more than an hour, we cut in this order: **Price agent → Hindi → escalation checklist**. The hero chain and the eval slide are never cut.

## Sponsor tracks

**Core:**
- **Fetch.ai:** ASI:One plus agents reacting to each other.
- **Anthropic:** the eval score and the quote checker.
- **Cartesia:** the live payroll call, with a written-request escalation when payroll stalls or refuses (the Hindi voice call was cut; see the Cartesia section).
- **Convex:** the live dashboard.
- **Capital One Nessie:** the refund deposit closing the case.

**Add-ons, only if working by freeze:** Apify, Bright Data, Microsoft Built for the Real World, CRS (credit agent), Notability, Best People-First Hack.

## Live pitch (2 minutes)

1. **0:00 to 0:15, hook:** "Priya's been losing $55 every paycheck and has no idea." (Use a real student quote.)
2. **0:15 to 0:45, notice:** "check my pay" in ASI:One makes the feed light up with $440.64 flagged, the IRS clause on screen, and the 24-hour week.
3. **0:45 to 1:15, act:** Priya says yes and the phone on the table rings. The call log appears.
4. **1:15 to 1:35, remember:** "simulate 2 weeks" lands the $440.64, and the case closes.
5. **1:35 to 2:00, prove it:** "Plain Claude: X of 25. Docket: Y of 25, every answer sourced." Close with: *"Claude can answer a question. It can't notice the one you didn't know to ask."*

## Rules we never break

- Code does all math, counting, and decisions. Claude transcribes and explains.
- No rule is shown without a quote that matches the stored source word for word.
- The call agent always says it's an AI and that the call may be recorded. It never pretends to be the student.
- Nothing is sent or called without the student's approval.
- Synthetic data only. Mask any SSN. The student can delete everything.
- Every flag says "likely" and points to the school's international office. **Not tax or immigration advice.**

## Open issues

See [`docs/PLAN_NOTES.md`](docs/PLAN_NOTES.md). The data and rules layer (seed, rules engine, quote checker, Nessie) is documented in [`docs/DATA_AND_RULES.md`](docs/DATA_AND_RULES.md).

## Setup

```bash
python3.12 -m venv .venv && source .venv/bin/activate   # uAgents does not support 3.14
pip install -r requirements.txt && npm install
cp .env.example .env   # fill in keys and a long random *_SEED per agent; never commit it
npx convex dev         # deploys convex/ and keeps it in sync; leave running
```

## Run the demo

```bash
.venv/bin/python -m seed.fetch_sources   # official IRS / eCFR text into `sources` (once)
.venv/bin/python -m seed.reset           # wipe demo state, re-seed Priya and the simulated cohort (before every rehearsal)
./scripts/run_agents.sh                  # Tax, Caseworker and Coordinator agents
npm run dashboard                        # live dashboard at http://localhost:5173
```

Then in ASI:One, open **docket-coordinator** (or start the message with its `@agent1...` handle;
messages sent with **To: ASI:One** go to ASI:One's own assistant, not to Docket) and try
`check my pay`, `what's wrong?`, `yes, contact payroll`.

Without ASI:One, the same conversation over the real chat protocol:

```bash
.venv/bin/python -m scripts.chat_test "check my pay" "what's wrong?" "yes, contact payroll"
```

## Sponsor tools

<!-- One section per sponsor: exactly what the tool does in the product. -->

### Capital One Nessie

Nessie is Priya's bank. `seed/reset.py` creates her customer, a checking account, 8 payroll deposits of $664.92 from "University Dining Payroll", 20 purchases (rent, groceries, phone, a $70 table) and 2 family transfers from India with the rupee amount and rate in the memo. The Ledger agent polls her deposits and purchases every 30 seconds and writes each one to Convex with its Nessie id, so re-polling never duplicates a row. Each paystub is linked to the deposit of exactly its net pay within 3 days. "Simulate 2 weeks" creates the $440.64 "FICA refund" deposit through the Nessie API (`seed/release_refund.py`); the Ledger sees it, matches it to the open case within $1, and the case closes. That deposit is the moment the money comes back.

### Cartesia (the payroll call)

When Priya approves, Docket phones payroll with a Cartesia **Managed Agent**: a voice agent that asks for the refund, confirms a date and a reference number, and records what payroll said. Voice is how the case actually moves: payroll offices answer phones, and the call is the step a student is least likely to make on her own.

**How it works**
- **Placing the call:** `agents/caseworker/cartesia.py` starts the call with `POST /agents/calls`, passing the case id, student name, employer and amount as **dynamic variables**. Every approval, from ASI:One or the dashboard, places exactly one call (`cases:claimCall`).
- **During the call:** the agent uses two **webhook tools** served by Convex HTTP actions (`convex/http.ts`), both protected by a Bearer token (`CARTESIA_TOOL_TOKEN`). `get_case_summary` returns the facts, computed in code, never by the voice model. `log_call_outcome` records the result through the case state machine (`cases:logCallOutcome`).
- **System tools:** End call, Skip turn (payroll pulling up the account) and Voicemail detection (hang up without leaving tax details on a voicemail).
- **Outcomes:** `promised` waits for the refund deposit. `needs_student` schedules a three-way call. A first `stalled` or `refused` moves the case to **written request**: the Caseworker writes a formal letter citing the clause and asking for the refund, or for a written refusal she needs for IRS Forms 843 and 8316. "Follow up by phone" places a second call. A second stall or refusal escalates to the IRS checklist.
- **Rehearsal setting:** each case has a setting (cooperates, stalls once, refuses once), shown on the dashboard so the teammate playing payroll knows what to do. With `CARTESIA_SIMULATE=1`, a stand-in payroll call follows it with no phone, through the same webhooks.

**Setup:** see [`docs/CARTESIA.md`](docs/CARTESIA.md) for the agent's instructions and welcome message, the two tools field by field, the phone number and the `.env` values.

**Responsible use**
- The welcome message says it is an AI assistant calling with the student's permission, and that the call may be recorded. It never claims to be her.
- It shares only the refund request. The 20-hour flag is never in `get_case_summary` or the letter, by construction, and a test checks the letter.
- Nothing is called without the student's approval. The letter is prepared for her to send from her own email; Docket sends nothing on its own.
- For the demo, the payroll number is a teammate's phone.

**Known limitations**
- Tested end to end against a stand-in for Cartesia's API and in rehearsal mode. The real call depends on the dashboard setup in `docs/CARTESIA.md`. `CARTESIA_VERSION` is configurable because Cartesia's docs show two API versions.
- Payroll's answers are whatever the person on the phone says. "Stalls once" is a rehearsal instruction, not a behavior we can force.
- The written request is prepared, not emailed. No email integration was built.
- Call transcripts are not stored; only the agent's summary, promised date and reference number are.
- The Hindi voice call to a parent was cut for time and privacy. Hindi explanations exist in chat through the Coordinator.
- Real outbound calling to employers has consent and calling-hours rules (TCPA) that this demo does not handle.

**Secrets:** no keys are in the repo. `CARTESIA_API_KEY`, the agent and number ids and `PAYROLL_PHONE` live in `.env`, which is gitignored. The webhook token lives in Convex's environment (`npx convex env set CARTESIA_TOOL_TOKEN ...`) and in your local `.env` for rehearsals.

### Claude (paystub reading)

The Ledger agent sends each paystub PDF to Claude and asks it to copy the printed values as text, exactly as written. Claude never calculates: code parses every amount into integer cents, then checks that Social Security is 6.2% of gross, Medicare is 1.45%, hours times rate equals gross, and net matches a bank deposit. A mismatch is stored as a low-confidence warning on the paystub, never silently fixed. `python -m rules.demo_rejection` shows the other guardrail live: a made-up clause is checked against the stored IRS text, rejected, and logged to the activity feed next to the real quote, which passes.
