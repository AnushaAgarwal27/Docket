# The payroll call (Cartesia)

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
Webhook base URL for the shared deployment: `https://basic-magpie-317.convex.site`

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
| Method, URL | POST `https://basic-magpie-317.convex.site/cartesia/case-summary` | POST `https://basic-magpie-317.convex.site/cartesia/call-outcome` |
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
   curl -X POST https://basic-magpie-317.convex.site/cartesia/case-summary \
     -H "Authorization: Bearer $CARTESIA_TOOL_TOKEN" -H "Content-Type: application/json" -d '{"case_id":"<case id>"}'
   ```
3. Full call: `python -m seed.reset`, let the Ledger read the paystubs, say "check my pay" then "yes" in ASI:One (or click Approve on the dashboard). The phone rings within about 5 seconds. The dashboard shows "Placing the call", then "On the phone with payroll", then the call log.

If the call cannot start, the dashboard and the activity feed say why (missing setting, bad number, Cartesia error). The case stays in `contacting_employer` and is not retried automatically, so nobody gets called twice. To retry, clear `callRequestedAt` and `callError` on the case in the Convex dashboard.

## Responsible use
- The agent says it is an AI assistant acting with the student's permission, and that the call may be recorded, before anything else.
- It never claims to be the student and shares only the refund request. The 20-hour flag is never sent to payroll: `get_case_summary` leaves it out by construction.
- Nothing is called without the student's approval: calls start only for cases in `contacting_employer`, which only `cases:approve` sets.
- For the demo, `PAYROLL_PHONE` is a teammate's phone. Real outbound calling has consent and calling-hours rules (TCPA); check before calling a real employer.
