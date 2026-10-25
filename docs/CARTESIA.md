# The voice layer (Cartesia)

Docket has two Cartesia voice agents, and they do different jobs.

| | `CARTESIA_AGENT_ID` — the payroll caller | `CARTESIA_STUDENT_AGENT_ID` — the student line |
|---|---|---|
| Direction | outbound only | outbound **and** inbound |
| Talks to | an employer's payroll office | the student |
| Started by | the Caseworker, on an approved case | a queued `voice` notification, or she dials in |
| Knows | one case, and nothing else about her | her whole file, and nothing about anyone else |
| Can do | ask for one refund, record the answer | read her what is open, take a question, record a yes or no |

Both read their facts live from Convex through webhook tools, so neither voice model holds a number
of its own. What they are allowed to say is decided before the call by `agents/guard.py`.

## The demo redirect — read this first

While `DEMO_CALL_REDIRECT=1` (the default), **`DEMO_CALL_NUMBER` is the only phone that rings**,
whoever the call is for. The intended number still travels with the call as the `intended_number`
dynamic variable and is shown on the dashboard's call row, so a redirected call is visible rather
than quietly going somewhere else.

This is what makes it safe for the research agent to find real payroll and legal-aid numbers and
store them as contacts: finding a number and dialling it are separate steps, and only the second one
is gated. Turn the redirect off (`DEMO_CALL_REDIRECT=0`) only when you mean to dial real people, and
read "Responsible use" at the bottom first.

---

# The payroll call

When Priya approves (by replying YES in ASI:One or with the dashboard button), Docket calls payroll with a Cartesia voice agent and records what payroll promised.

```
approve ──> case: contacting_employer
             │  Caseworker claims the case once (cases:claimCall), then
             ▼  POST https://api.cartesia.ai/agents/calls  {agent_id, from_number_id, to_number, dynamic_variables: {case_id, ...}}
        Cartesia voice agent calls PAYROLL_PHONE
             │  tool get_case_summary  ──> POST <convex site>/cartesia/case-summary   (facts computed in code)
             │  tool log_call_outcome  ──> POST <convex site>/cartesia/call-outcome   (runs cases:logCallOutcome)
             ▼
        case: awaiting_response (promised) | awaiting_response + 3-way call (needs_student)
              | written_request (first stall or refusal: letter, then "Follow up by phone" places call 2)
              | escalate_irs (stall or refusal again after the letter)
```

Code: `agents/caseworker/cartesia.py` (starts the call), `agents/caseworker/engine.py` (`request_call`, `place_pending_calls`),
`convex/http.ts` and `convex/cartesia.ts` (the two webhook tools), `cases:claimCall` / `cases:recordCallStart` (one approval, one call).

## One-time setup (about 15 minutes)

### 1. Webhook password on Convex
Whoever runs `npx convex dev` for the shared deployment:
```
openssl rand -hex 24                         # copy the output
npx convex env set CARTESIA_TOOL_TOKEN <that value>
```
Your webhook base URL is your **own** deployment's site URL — not a teammate's. Print it with:
```
.venv/bin/python -m scripts.check_voice
```
It is your `CONVEX_URL` with `.convex.cloud` swapped for `.convex.site`. Pasting someone
else's here is the most common way to lose an hour: the tools return 401 or talk to the wrong
student file, and nothing in Cartesia says why.

### 2. Agent in the Cartesia dashboard
Create a managed agent, for example "Docket payroll caller". English, any clear voice. Turn on the **End call** system tool.

**Initial message**
```
Hi, this is Docket, an AI assistant calling on behalf of {{student_name}}, with her permission. This call may be recorded. Am I speaking with payroll?
```

**Instructions**
```
You are Docket's payroll assistant, calling {{employer}} payroll on behalf of {{student_name}}, an F-1 international student, with her written permission.

- You are an AI assistant. Say so at the start and whenever asked. Never claim to be {{student_name}} or a human.
- Right after payroll answers, call get_case_summary once and use only the facts it returns. Never make up numbers, dates, or rules.
- Ask for exactly two things: a refund of {{refund_amount}}, and that Social Security and Medicare stop being withheld from her future paychecks.
- Then ask when the refund will be issued and for a reference number. Repeat both back to confirm.
- Share nothing else about {{student_name}}: no work hours, visa history, bank details, or ID numbers. If asked, say she will follow up directly.
- If payroll needs to speak with her or needs documents, do not argue; record needs_student.
- If payroll says no, stay polite, ask whether they can put that in writing, and record refused.
- If payroll will not commit to a date, record stalled. Do not push.
- Before ending, always call log_call_outcome. Give promised_by as YYYY-MM-DD.
- Then thank them and end the call. Keep every reply to one or two short sentences.
```

### 3. Two webhook tools
Create both as webhook tools and attach them to the agent. Auth: **Bearer**, token = the `CARTESIA_TOOL_TOKEN` value.

| | get_case_summary | log_call_outcome |
|---|---|---|
| Description | Get the facts of this refund request: amount, pay periods, the rule, and what to ask for. Call once, right after payroll answers. | Record what payroll agreed to. Call once, before ending the call. |
| Method, URL | POST `<your site URL>/cartesia/case-summary` | POST `<your site URL>/cartesia/call-outcome` |
| Body | `case_id` ← dynamic variable `case_id` | `case_id` ← dynamic variable `case_id`; `result` (string, model, enum): `promised`, `stalled`, `refused`, `needs_student`; `answered_by` (string, model): name or role of the person; `summary` (string, model): one sentence on what payroll said; `promised_by` (string, model, optional): refund date as YYYY-MM-DD; `reference_number` (string, model, optional) |
| Pre-tool speech | off | auto |
| Execution | immediate | immediate |
| Timeout | 10 s | 10 s |

### 4. Phone number and .env
Get a Cartesia phone number. Then in the repo-root `.env` of the machine that runs the Caseworker:
```
CARTESIA_API_KEY=sk_car_...
CARTESIA_AGENT_ID=...
CARTESIA_FROM_NUMBER_ID=...
PAYROLL_PHONE=+1XXXXXXXXXX      # the teammate playing payroll, E.164
# CARTESIA_VERSION=2026-08-14   # change only if Cartesia's API version for /agents/calls differs
```
Restart the Caseworker (`python -m agents.caseworker.agent`, or `scripts/run_agents.sh`).

## Rehearse without a phone
Set `CARTESIA_SIMULATE=1` and `CARTESIA_TOOL_TOKEN` in `.env` and restart the Caseworker. Approvals then run a stand-in call that
plays the agent's two tools against Convex and follows the case's **Rehearsal setting** (dashboard): cooperates, stalls once or
refuses once on the first call, then agrees on the follow-up. Activity rows say "Rehearsal: simulated payroll call". Unset it
for the real call. With a real call, the rehearsal setting is only an instruction for the teammate playing payroll.

## Test it
1. Playground: in the Cartesia dashboard, set the sample dynamic variable `case_id` to a real case id (copy it from the Convex dashboard, `cases` table) and talk to the agent. Both tools should return text, and the case should move to `awaiting_response`.
2. Webhooks alone:
   ```
   .venv/bin/python -m scripts.check_voice --probe
   ```
3. Full call: `python -m seed.reset`, let the Ledger read the paystubs, say "check my pay" then "yes" in ASI:One (or click Approve on the dashboard). The phone rings within about 5 seconds. The dashboard shows "Placing the call", then "On the phone with payroll", then the call log.

If the call cannot start, the dashboard and the activity feed say why (missing setting, bad number, Cartesia error). The case stays in `contacting_employer` and is not retried automatically, so nobody gets called twice. To retry, clear `callRequestedAt` and `callError` on the case in the Convex dashboard.

---

# The student line

One agent, both directions. Create it the same way as the payroll caller: a managed agent in the
Cartesia dashboard, **End call** system tool on, assigned a phone number so inbound calls reach it
(`cartesia phone-numbers assign <phone-number-id> --agent-id <agent-id>`). Put its id in
`CARTESIA_STUDENT_AGENT_ID`.

**Initial message**
```
Hi {{student_name}}, this is Docket. {{headline}}
```
On an inbound call `student_name` and `headline` are empty, so start with: *"Docket, how can I help?"*

**Instructions**
```
You are Docket's student line, speaking with an F-1 international student about her own pay and
immigration status. You are an AI assistant; say so if asked, and never claim to be a person.

FIRST, ALWAYS:
- If profile_id is empty, this is an inbound call: call identify_caller with the caller's number
  before anything else, and use the profile_id it returns for every other tool.
- If profile_id is set, this is a call Docket placed. Open with the headline you were given, which
  has already been checked. Do not add figures to it.

WHAT YOU MAY DO
- Call get_student_brief to tell her what is open on her file.
- If she asks anything you were not told, call answer_question. Use its answer word for word.
  If it says the question has been handed to research, say so and promise the answer as a message.
  NEVER guess at a tax, visa or immigration answer. An "I don't know yet, I'll find out" is correct;
  a plausible invention is not.
- If she wants to approve or decline something — a refund request, a form, joining a group case —
  make sure you have said what it is, then call record_student_decision with subject and a plain
  yes or no. If her answer is unclear, ask again; never read a maybe as a yes.
- Before ending, call log_student_call with a one-sentence summary.

WHAT YOU MAY NOT DO
- Discuss anyone else, or confirm that any other student exists. A group case is "other students",
  a count and an employer, never a name.
- Read out bank details, identity numbers or her phone number.
- Give tax or legal advice, or tell her what will happen to her visa. Point her to her
  international student office for anything turning on her individual status.

Keep every reply to one or two short sentences. She may be worried about money; be calm and plain.
```

**Five webhook tools**, all POST, all Bearer `CARTESIA_TOOL_TOKEN`, all against the Convex site URL:

| Tool | Path | Body |
|---|---|---|
| `identify_caller` | `/cartesia/identify` | `from_number` ← the caller's number |
| `get_student_brief` | `/cartesia/student-brief` | `profile_id` |
| `answer_question` | `/cartesia/ask` | `profile_id`; `question` (string, model) |
| `record_student_decision` | `/cartesia/decision` | `profile_id`; `subject` (enum: `refund`, `document`, `group`); `answer` (enum: `yes`, `no`) |
| `log_student_call` | `/cartesia/student-call` | `profile_id`; `summary` (string, model); `direction` (enum: `inbound`, `outbound`); `purpose`; `notification_id` |

Dynamic variables Docket sets on an outbound call: `profile_id`, `student_name`, `purpose`,
`headline`, `notification_id`, `intended_number`.

## Consent gates it on our side too
Docket will not ring her unless `profiles.voiceConsent` is true and `profiles.phone` is set — she
sets both herself, in chat ("call me"), or on the dashboard. A call skipped for lack of consent is
logged with that reason rather than silently dropped, and the message falls back to chat.

## Responsible use
- The agent says it is an AI assistant acting with the student's permission, and that the call may be recorded, before anything else.
- It never claims to be the student and shares only the refund request. The 20-hour flag is never sent to payroll: `get_case_summary` leaves it out by construction.
- Nothing is called without the student's approval: calls start only for cases in `contacting_employer`, which only `cases:approve` sets.
- For the demo, `DEMO_CALL_NUMBER` is the only phone that rings, whatever the call is for. Real outbound calling has consent and calling-hours rules (TCPA); check before turning `DEMO_CALL_REDIRECT` off and calling a real employer.
- The student line never rings without her consent (`profiles.voiceConsent`), and it will not discuss a file with a number it does not recognise — it says so and ends the call rather than guessing who is on the line.
- The student line refuses to answer a tax or status question it was not given an answer for. Handing the question to research and texting the answer later is the designed behaviour, not a failure.
- A contact the research agent finds is stored unverified and is still never dialled on its own; it is shown to the student so she can decide.
