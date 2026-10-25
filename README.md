![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)
![tag:hackathon](https://img.shields.io/badge/hackathon-5F43F1)

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

Four layers, each with one job. The layer boundaries are the point: the research layer can be wrong
without anything wrong being *said*, and the voice layer can be talking to anyone without learning
anything it should not.

```
   ┌─ VOICE ─ Cartesia ──────────────────────────────────────────────────────┐
   │  she calls Docket and asks anything · Docket calls her when she's needed │
   │  Docket calls payroll with her approval · texts and chat                 │
   └──────────────────────────────┬──────────────────────────────────────────┘
                                  │  every word crosses this line
   ┌─ GUARDRAIL ─ Claude ─────────┴──────────────────────────────────────────┐
   │  redacts by audience · writes for the channel · then CODE checks it:    │
   │  no amount outside the facts, no quote not in a verified source,        │
   │  no phone number we didn't supply. Rejected text falls back to code.    │
   └──────────────────────────────┬──────────────────────────────────────────┘
                                  │
   ┌─ AGENTS ─ Fetch.ai uAgents ──┴──────────────────────────────────────────┐
   │  Ledger      Nessie bank, paystubs, refund matching                     │
   │  Tax         rules in code; argues the student's side (Advocate)        │
   │  Auditor     argues the employer's side; the verdict, in code           │
   │  Caseworker  case state machine, approvals, calls, letters              │
   │  Researcher  Athena: deep research + news watch, sources verified       │
   │  Organizer   finds employers with a pattern; runs the group request     │
   │  Filer       fills her forms in; submits only what she approved         │
   │  Coordinator the one she talks to in ASI:One                            │
   └──────────────────────────────┬──────────────────────────────────────────┘
                                  │
           Shared student file on Convex · Nessie is the bank
   profiles · transactions · paystubs · sources · flags · hearings · cases · calls
   notifications · research · documents · groups · groupMembers · contacts · activity
                                  │
                           Live dashboard
                  (activity feed, cases, money)
```

- 8 agents (Coordinator, Ledger, Tax, Auditor, Caseworker, Researcher, Organizer, Filer), each a **Fetch.ai uAgent** in Python 3.12/3.13. Only the Coordinator speaks the chat protocol to ASI:One.
- **Convex** is the shared student file. The dashboard shows every row the moment it lands.
- **Nessie** feeds the Ledger, official sources are fetched into `sources`, and **Cartesia** makes the calls.

### The shared file ([`convex/schema.ts`](convex/schema.ts))

| Table | Holds | Written by | Read by |
|---|---|---|---|
| `profiles` | Visa, arrival date, school, home country/currency, work auth, masked phone | Coordinator | Every agent |
| `transactions` | Every Nessie deposit, purchase, and transfer | Ledger | Tax, Caseworker, dashboard |
| `paystubs` | Period, gross, hours by week, SS/Medicare withheld, net, employer | Ledger | Tax, dashboard |
| `sources` | Official page URL, fetched text, fetch time, content hash | Apify collector | Tax, quote checker |
| `flags` | Rule id, amount, explanation, quoted clause, source id, status | Tax | Caseworker, dashboard |
| `cases` | Flag id, state, amount owed, deadlines, next follow-up, outcome | Caseworker | Ledger, dashboard |
| `calls` | Who answered, summary, promised date, reference no., transcript | Caseworker (Cartesia webhook) | Caseworker, dashboard |
| `activity` | Agent, action, inputs/outputs, source id, timestamp | **Every agent, every action** | Dashboard feed |

**The one rule for `activity`:** every agent writes one row for every action it takes, *including actions it decided not to take*. The dashboard feed is just this table, newest first.

Money is stored in **integer cents everywhere**. No floats, and no numbers written by the model.

## The agents

**1. Coordinator** is the only agent Priya talks to. It's a uAgent with a mailbox and the chat protocol, reachable in ASI:One. It handles intents like "check my pay", "what's wrong?", "yes, contact payroll", "is $70 normal for a table?", and "explain in Hindi". It sends approval prompts as ASI:One Interactive Cards ([`agents/coordinator/cards.py`](agents/coordinator/cards.py)), with the narration text as the fallback if a client can't render them, and its echo guard ignores ASI:One replaying our own replies.

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

**5. Auditor** argues the employer's side of every finding before it reaches the student (the Hearing), and issues the verdict in code. The Price agent from the original plan was cut.

**6. Researcher (Athena)** answers what the student file cannot, and watches for what changes it.
- A question she asks on the phone that the file cannot answer is recorded, not guessed at. This agent researches it and sends the answer back as a message.
- It runs on ASI:One's agentic models — Fetch.ai's deep-execution layer, which plans the research and can call other agents on Agentverse — and falls back to Claude with web search.
- **Every source is then fetched by code and has to contain the claim's wording before it counts.** A page that 404s or does not support the answer is dropped, and an answer left with no surviving source is marked low confidence and never stated as fact.
- What leaves for a third-party research service is built by allow-list — visa category, rule id, employer *kind* — with her name, employer, school, phone and amounts stripped in code first.

**7. Organizer** notices when several students at one employer have the same finding, and gets them asking together. One student is easy to put off; four is a payroll configuration error. **Nobody is in the combined request until they say yes**: an invited student's amount is not in the total and their name is not in the letter. The invitation gives a count and an employer, never another student's name or amount. Joining never pauses or weakens her own case.

**8. Filer** fills her forms in — Form 8843, the refund letter, and Forms 843 and 8316 for the IRS route — and submits only what she approved. Every field is computed in code from a stored record and shows which record, so nothing on a tax form was written by a model. A missing fact stops the form rather than being filled with a plausible guess. Docket cannot file with the IRS, and says so plainly instead of implying it did.

## The guardrail layer ([`agents/guard.py`](agents/guard.py))

Everything a person reads or hears goes through one module, in three steps.

1. **Redact.** Each audience gets its own allow-list of facts. Payroll never receives work hours, an arrival date, bank rows or another student's name, because those keys are not in its slice — there is nothing to leak. A group message can carry a count and an employer and nothing that could identify a person.
2. **Convert.** Claude turns the redacted facts into words for one channel: a sentence a voice agent can speak, a text short enough to send, a chat reply, a paragraph for a document.
3. **Check.** Code reads what came back and rejects it unless every dollar amount is in the facts, every quoted sentence is word for word in a verified source, no phone number appears that we did not supply, and the text fits the channel. A rejected render falls back to a sentence written entirely in code.

Claude writes the words. It never decides the money, the rule or the recipient, and it cannot widen its own audience.

## The voice layer ([`docs/CARTESIA.md`](docs/CARTESIA.md))

Two Cartesia agents. The **payroll caller** asks one employer for one refund. The **student line** works both ways: Docket rings her when something needs her, and she can ring the same number and ask anything.

Three things the student line will not do: discuss a file with a number it does not recognise, read a maybe as a yes, or answer a tax or status question it was not given an answer for — an unknown question is handed to the research agent and the answer arrives as a message.

**The demo redirect:** while `DEMO_CALL_REDIRECT` is on, `DEMO_CALL_NUMBER` is the only phone that rings, whoever the call is for. The intended number still travels with the call and is shown on the dashboard, so a redirected call is visible rather than quietly going elsewhere. That is what makes it safe for the research agent to find real payroll and legal-aid numbers: finding a number and dialling it are separate steps, and only the second is gated.

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

Each track below says what the tool actually does in the product, what the judges for that track are
looking for, and where the evidence is. Nothing here is aspirational — if it isn't built, it says so.

### Fetch.ai — ASI:One Agent Challenge: *From Intent to Action*

The headline track, and the one the architecture is shaped around. The challenge asks for an agent
discovered through ASI:One that understands intent and **takes action** — explicitly "more than a
chatbot or a thin wrapper around an API."

Docket's answer: **a student types "check my pay" in ASI:One, and a phone rings in a payroll office.**

| Mandatory requirement | How |
|---|---|
| Agent registered on Agentverse | **8 uAgents**, each `mailbox=True, publish_agent_details=True` with its own published README |
| Agent Chat Protocol | `Protocol(spec=chat_protocol_spec)` on the Coordinator; `ChatMessage` in, `ChatAcknowledgement` out |
| Discoverable and usable via ASI:One | Every agent publishes tags, features and example queries from its `AGENTVERSE.md` |
| Meaningful tool execution / orchestration | 8 agents, 22 typed message types, a 4-agent adversarial Hearing, plus telephony, banking, crawling and live web research |
| Whole workflow inside ASI:One | `check my pay` → sourced findings → `yes` → real call → refund tracked → case closed. The dashboard is a bonus view, not a dependency |
| Public repo with run instructions | [Setup](#setup) and [Run the demo](#run-the-demo) |

**Bonus criteria:** multi-agent collaboration (the Hearing), ASI Interactive Cards
([`agents/coordinator/cards.py`](agents/coordinator/cards.py) — form, detail and review, validated
before send), reliability and recovery from failed tool calls (below), real-time data, and a system
that keeps working after the hackathon. **The Payment Protocol is not implemented** — the one bonus
criterion we skipped, and we don't claim it.

**The two things worth arguing in front of a judge.**

*Agents that disagree.* Before a finding reaches the student, the Tax agent claims it, the Auditor
objects on the employer's behalf, Tax rebuts from the file, and the Auditor issues a verdict **in
code**. A verdict that isn't `upheld` opens no case. One model arguing with itself in a prompt is
theatre; two agents holding separate state is a check.

*Recovery that came from a real failure.* The voice agent reports call outcomes through a webhook.
Ours was misconfigured, so a call completed, payroll made a real promise, and the case silently sat
forever. [`agents/caseworker/call_record.py`](agents/caseworker/call_record.py) now reads Cartesia's
own record of its calls every 45 seconds and recovers the outcome — refusing any promised date that
doesn't parse or sits in the past, and downgrading anything uncertain to "stalled" rather than
inventing a promise. A real promise shouldn't be lost because a webhook was.

Full track breakdown and the video script: **[`docs/DEMO_FETCHAI.md`](docs/DEMO_FETCHAI.md)**.

### Anthropic — Claude

Claude is used in four places and is **never allowed to decide anything**: it transcribes paystubs,
phrases findings, converts facts into words for a channel, and classifies a call summary into one of
four fixed outcomes. Code does all math, all rule evaluation, and every state transition.

The interesting part is the third one. Every sentence a person reads or hears crosses
[`agents/guard.py`](agents/guard.py): facts are redacted to an allow-list for that audience, Claude
writes from the redacted slice, then **code rejects the result** unless every dollar amount is in the
facts, every quoted sentence is word for word in a verified source, and no phone number appears that
we didn't supply. A rejected render falls back to a sentence written entirely in code. Payroll never
hears about her work hours because those keys aren't in payroll's slice — there is nothing to leak.

Evidence on camera: `python -m rules.demo_rejection` rejects a fabricated clause and passes the real
one, both logged to the activity feed.

### Cartesia — voice

A two-way voice layer. Docket calls payroll on the student's approval, reads the live case file
mid-call through a webhook tool, and records what payroll said. The call states that it is an AI
calling with the student's permission and that the call may be recorded; it never pretends to be her.

Voice is the step that matters because payroll offices answer phones, and calling one is the thing a
student is least likely to do herself.

Details, setup and the responsible-use notes: [`docs/CARTESIA.md`](docs/CARTESIA.md) and the
[Cartesia section](#cartesia-the-payroll-call) below.

### Convex — the shared student file

Every agent reads and writes one reactive database, and every dashboard panel is a live query. No
agent calls another to tell it what to do: the Ledger writes a paystub, the Tax agent notices. The
case state machine runs in Convex mutations, so an invalid transition is rejected at the database
rather than argued about in Python. The voice agent's webhook tools are Convex HTTP actions.

### Capital One Nessie — the bank

Nessie is Priya's actual bank account, not a mock. The seed creates her customer, 8 payroll deposits,
20 purchases and 2 family transfers from India. The Ledger polls it, dedupes on the Nessie id, and
matches each paystub to the deposit of exactly its net pay within 3 days. **"Simulate 2 weeks" creates
the real $440.64 refund deposit through the Nessie API** — the Ledger sees it, matches it to the open
case within $1, and the case closes. That deposit is the moment the money comes back.

### Apify — official sources

Every rule quotes a page that Apify fetched: IRS Pub 519, 8 CFR 214.2 on eCFR, the Form 8843 page.
Each is stored with its fetch time and a sha256. When a hash changes, Docket logs `source_changed`,
re-checks that rule's quote, and **holds the rule's flags back** if the sentence is no longer on the
page. That is what makes this hold up after the hackathon: the law moves, and we notice.

## Demo videos

| Video | Guide |
|---|---|
| Fetch.ai track (4 min) — Agentverse, uAgents, ACP, ASI:One, the Hearing | [`docs/DEMO_FETCHAI.md`](docs/DEMO_FETCHAI.md) |
| Main submission (3 min) — the whole story, all sponsors | [`docs/DEMO_VIDEO.md`](docs/DEMO_VIDEO.md) |

Both include a pre-flight checklist, a shot list with timings, the exact words to type into ASI:One,
and what to do when something breaks mid-shoot.

One command puts the demo in a clean, recordable state:

```bash
.venv/bin/python -m scripts.demo_reset   # ~1 min: seed, 8 paystubs, rules, $440.64 case open
```

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
cp .env.example .env   # fill in the keys; never commit it
.venv/bin/python -m scripts.make_seeds   # prints the agent seeds you are missing, to paste into .env
npx convex dev         # deploys convex/ and keeps it in sync; leave running
```

An agent's Agentverse address is derived from its seed, so once an agent is registered its seed must
not change. `make_seeds` prints only the ones that are missing, so re-running it is safe.

## Run the demo

```bash
.venv/bin/python -m seed.fetch_sources   # official IRS / eCFR text into `sources` (once)
.venv/bin/python -m seed.reset           # wipe demo state, re-seed Priya and the simulated cohort (before every rehearsal)
./scripts/run_agents.sh                  # all eight agents; refuses to start if a seed is missing
npm run dashboard                        # live dashboard at http://localhost:5173
```

Then in ASI:One, open **docket-coordinator** (or start the message with its `@agent1...` handle;
messages sent with **To: ASI:One** go to ASI:One's own assistant, not to Docket) and try
`check my pay`, `what's wrong?`, `yes, contact payroll`.

The rest of what she can do there:

| Say | What happens |
|---|---|
| `my forms` | the filled-in form, field by field, with the record each value came from, and Approve / Not yet |
| `anyone else?` | other students at her employer with the same finding, and the option to join them |
| `call me` | her phone number and whether Docket may call or text her — nothing is dialled without this |
| anything else about F-1 pay, tax or status | goes to the research agent, which answers with sources it verified, or says it could not |

The dashboard has a tab for each of these — **Messages** (everything Docket told her, on any channel,
and whether it reached her), **Forms**, **Group**, **Research** — plus the original Overview,
Paystubs, Cases, Activity and Tracks.

Without ASI:One, the same conversation over the real chat protocol:

```bash
.venv/bin/python -m scripts.chat_test "check my pay" "what's wrong?" "yes, contact payroll"
```

Live scenario checks against the running agents (resets the demo first): agents noticing new paystubs on
their own, indirect wording, the next-season answer, explicit approval, the proactive refund message, and
the Agentverse readme:

```bash
.venv/bin/python -m eval.scenarios
```

## Sponsor tools

<!-- One section per sponsor: exactly what the tool does in the product. -->

### Fetch.ai (the agents, Agentverse and ASI:One)

Docket is **eight uAgents**. Each owns one decision nobody else is allowed to make, which is what
makes them able to check each other rather than just relay to each other.

| Agent | Port | Owns |
|---|---|---|
| `docket-coordinator` | 8001 | The only agent the student talks to: chat protocol, cards, narration |
| `docket-ledger` | 8002 | Nessie bank feed, paystub PDFs, refund matching |
| `docket-tax` | 8003 | The rules, in code; argues the student's side (Advocate) |
| `docket-auditor` | 8006 | Argues the employer's side; issues the verdict in code |
| `docket-caseworker` | 8004 | Case state machine, approvals, payroll calls, letters |
| `docket-researcher` | 8005 | Athena: deep research and news watch, every source verified |
| `docket-organizer` | 8007 | Finds employers with a shared pattern; runs the group request |
| `docket-filer` | 8008 | Fills forms from stored records; submits only what she approved |

Print the live addresses and Agentverse inspector links with
`.venv/bin/python -m scripts.print_agents --plain`. An address is derived from its seed, so **once an
agent is registered its seed must not change**; `scripts.make_seeds` only prints the ones missing.

**Agentverse.** Every agent runs `mailbox=True` with `publish_agent_details=True` and a
`readme_path` pointing at its own `AGENTVERSE.md` (tags, features, example queries). Being listed in
the Almanac is not proof the mailbox exists, so [`agents/agentverse.py`](agents/agentverse.py) asks
Agentverse for the agent's own mailbox at startup, signed by the agent, and logs the answer to the
console *and* the activity feed. A missing **Connect → Mailbox** click shows up as a warning with the
inspector URL rather than as a silent ASI:One failure.

**Agent Chat Protocol.** `Protocol(spec=chat_protocol_spec)` on the Coordinator
([`agents/coordinator/agent.py`](agents/coordinator/agent.py)): it acknowledges every `ChatMessage`
before answering, sends one `ChatMessage` per part so a card and its narration stay separate, and
marks only the last one as ending the session. An echo guard drops ASI:One replaying our own replies.

**Agent-to-agent.** 22 typed `Model` messages in [`agents/messages.py`](agents/messages.py) —
`RunRules`, `OpenCases`, `CaseDecision`, `Claim`, `Objection`, `Rebuttal`, `Verdict`, `CaseOpened`,
`WatchRefund`, `ResearchQuestion`, `PatternFound`, `GroupInvite`, `FillDocument` and the rest. A
`LocalFirstResolver` routes to a local port when the agent is on this machine and through Agentverse
otherwise, so the same code runs in both. Senders are checked: the Caseworker ignores a `Verdict`
that didn't come from the Auditor's address.

**ASI:One Interactive Cards.** [`agents/coordinator/cards.py`](agents/coordinator/cards.py) builds
form, detail and review cards as `MetadataContent` with `card_protocol_version "1"`, used for profile
capture, refund approval, group invites and document review. Every card is validated before it is
sent — field kinds, CTA shape, 64 KB payload cap — and the narration text above it is the fallback if
the card is rejected, so a client that can't render cards still gets a usable message. Every number
on a card is read from the student file; nothing there computes money.

**ASI:One agentic models.** The Researcher's primary engine is `asi1` at `api.asi1.ai`
([`agents/researcher/athena.py`](agents/researcher/athena.py)), which plans a research task and can
discover and call other agents on Agentverse; Claude with web search is the fallback. Either way the
answer has to earn its sources: **every URL is re-fetched in code and must actually contain the
claim's wording**, or it's dropped, and an answer with no surviving source is marked low confidence
and never stated as fact.

**Known limitations**
- One student profile at a time. Multi-student lookup needs onboarding we didn't build.
- Agents run on our machines, so ASI:One only reaches Docket while they're up.
- The Fetch.ai **Payment Protocol is not implemented**.
- Cards are validated against the published spec but have only been exercised in our own client and
  ASI:One; an unusual renderer may fall back to the text.

**Secrets:** every agent seed lives in `.env`, which is gitignored. `ASI_ONE_API_KEY` too.

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

### Apify (official sources)

Apify fetches the official pages every rule quotes: IRS Pub 519, 8 CFR 214.2 on eCFR, the IRS Form 8843 page and the IRS page on nonresident returns. `python -m seed.apify_sources` runs Apify's Website Content Crawler once for all of them (plain HTTP, depth 0, raw HTML kept), extracts the text with the same code as before, and stores each page in Convex `sources` with its fetch time and sha256. When a page's hash differs from the stored copy, it logs `source_changed` to the activity feed and checks that rule's quote again; a quote that is no longer on the page means the Tax agent holds that rule's flags back until a person updates `rules.yaml`. `python -m rules.download_sources --apify` does the same into `sources/*.txt` for offline checks (`rules.verify_sources`, `eval.score`). Run it on a schedule to watch for changes.
