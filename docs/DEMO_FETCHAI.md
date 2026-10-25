# Fetch.ai demo: ASI:One Agent Challenge

Everything needed to record the Fetch.ai track video, and the evidence for every claim it makes.

The challenge is **"From Intent to Action"**: build an agent that is discovered through ASI:One,
understands intent, and *takes action*. The line that matters in the judging is "more than a chatbot
or a thin wrapper around an API."

Docket's answer: **a student says "check my pay" in ASI:One, and a phone rings in a payroll office.**
Nothing in between is typed by a person. That is the whole video.

---

## 1. Compliance: every requirement, and where it lives

### Mandatory

| Requirement | Status | Evidence |
|---|---|---|
| Register at least one agent on Agentverse | **8 agents** | `mailbox=True, publish_agent_details=True` on every agent; roster in [`agents/agentverse.py`](../agents/agentverse.py). Addresses in §2. |
| Implement the Agent Chat Protocol (ACP) | **Yes** | `Protocol(spec=chat_protocol_spec)` — [`agents/coordinator/agent.py:51`](../agents/coordinator/agent.py). Handles `ChatMessage`, replies with `ChatAcknowledgement`. |
| Discoverable and usable through ASI:One | **Yes** | Every agent publishes a README ([`AGENTVERSE.md`](../agents/coordinator/AGENTVERSE.md)) with tags, features and example queries, via `readme_path=`. |
| Meaningful tool execution or multi-agent orchestration | **Both** | 8 agents, 22 typed message types, a 4-agent adversarial Hearing (§4). Tools: Cartesia voice, Nessie banking, Convex, Apify, Claude, live web. |
| Primary workflow entirely inside an ASI:One conversation | **Yes** | `check my pay` → findings with sources → `yes` → real phone call → refund tracked → case closed. No frontend required. The dashboard is a bonus view, not a dependency. |
| Public GitHub repo with run instructions | **Yes** | [README](../README.md) → Setup, Run the demo. |

### Bonus

| Bonus criterion | Status | Evidence |
|---|---|---|
| Effective multi-agent collaboration | **Strong** | The Hearing: Tax argues for the student, Auditor argues for the employer, verdict decided in code. A finding reaches the student only if it survives. §4. |
| ASI Interactive Cards | **Yes** | [`agents/coordinator/cards.py`](../agents/coordinator/cards.py) — form, detail and review cards, `card_protocol_version "1"`, validated before send, 64 KB cap enforced. Used for profile capture, refund approval, group invites, document review. |
| Reliability, error handling, recovery from failed tool calls | **Strong** | [`agents/caseworker/call_record.py`](../agents/caseworker/call_record.py) — when the voice agent's `log_call_outcome` webhook never arrives, the Caseworker reads Cartesia's own record of the call and recovers the outcome. This is a real failure we hit and fixed. §5. |
| Creative use of real-time data and external services | **Yes** | Live Nessie bank feed, Apify crawling IRS/eCFR with content hashing, ASI:One agentic research with every source re-fetched and checked, outbound telephony. |
| Could realistically keep operating after the hackathon | **Yes** | Cases live for weeks with follow-up dates. Source hashing catches an IRS page changing under us. Nothing is demo-only except the seed data. |
| Payment Protocol | **Not implemented** | The one bonus criterion we did not build. Say so if asked; do not claim it. |

---

## 2. The agents

Eight uAgents. Each has a mailbox, a published README, and one job.

| Agent | Port | Does |
|---|---|---|
| **Coordinator** | 8001 | The only agent the student talks to. ACP + cards. |
| **Ledger** | 8002 | Nessie bank feed, paystub PDFs, refund matching. |
| **Tax** | 8003 | Runs the rules in code; argues the student's side (Advocate). |
| **Auditor** | 8006 | Argues the employer's side; issues the verdict in code. |
| **Caseworker** | 8004 | Case state machine, approvals, payroll calls, letters. |
| **Researcher** | 8005 | Athena: ASI:One agentic research + news watch. |
| **Organizer** | 8007 | Finds employers with a shared pattern; runs the group request. |
| **Filer** | 8008 | Fills forms from stored records; submits only what is approved. |

Addresses (print them yourself with `.venv/bin/python -m scripts.print_agents --plain`):

```
docket-coordinator  agent1qdcydhdy3drfp5amt48hqqspvyzu8ggv6me59v8rek7mvk8y4q6csnk3dz2
docket-ledger       agent1qfx8zr76aza0tvrxszqgzyu6skdf3ulr3kqflve9tewj2xdvj44q52m32vd
docket-tax          agent1qt4l5mr37zcvfhk0fqt9cs0pzlp60t5qy8vqcf3r2qlwlcu7gpkq79vevvr
docket-auditor      agent1qvqezkjvxsf7uv0eakd0mtvntx2tts5h7ceqejqcautyhqhc2t62kh7lvsl
docket-caseworker   agent1qdl8d9m2ul4sr7r48r5ayakwwhdm6x40j65ax5sjww6hc2m2hqezszkma2j
docket-researcher   agent1qtlke98gyp2ynpgn5ztpmps094kup2hwjd583u4jg4q62jt407dhj08y9nd
docket-organizer    agent1q25kkfyjnx9kp370e5qnqagx6hy065q7z7pvqa284tnckwvltnukvpqanzf
docket-filer        agent1qwf28zyfhmjrj0ygts5uugv8xjzwa3274apagvugym9s3h6v4fdpykc899r
```

An address is derived from its seed, so **a registered agent's seed must never change.**

### Why eight and not one

Each agent owns a decision nobody else is allowed to make. That is what makes the Hearing possible:
the Auditor can genuinely object to the Tax agent's finding because it holds different facts and
answers to different rules. One agent arguing with itself in a single prompt is theatre. Two agents
with separate state is a check.

---

## 3. Pre-flight (do this before recording)

```bash
# 1. Clean demo state — seeds Priya, reads 8 paystubs, runs the rules, opens the case
.venv/bin/python -m scripts.demo_reset          # ~1 min; Claude transcribes each paystub

# 2. Start all eight agents
./scripts/run_agents.sh                          # prints addresses + Agentverse inspector links

# 3. Dashboard (for the overall video; optional for the Fetch.ai one)
npm run dashboard                                # http://localhost:5173
```

Wait ~20 seconds after startup and check each agent logs `Agentverse mailbox: connected`. If one says
`not connected`, open its inspector link, click **Connect → Mailbox**, and restart that agent.

**Check before you hit record:**

- [ ] All 8 agents log `Agentverse mailbox: connected`
- [ ] `docket-coordinator` answers in ASI:One (send `hello`)
- [ ] `.venv/bin/python -m scripts.demo_ready` shows **$440.64**, state `contacting_employer`
- [ ] Phone with **+1 925 967 7432** is on the desk, ringer on, not silenced
- [ ] `DEMO_CALL_REDIRECT=1` in `.env` so every call lands on that phone
- [ ] `CARTESIA_SIMULATE` is **unset or 0** — a simulated call is not a demo

If `demo_ready` says `awaiting_approval`, that's correct and expected: **the video is you approving
it.** Only run `--arm` if you're rehearsing the call alone.

---

## 4. The showpiece: the Hearing

This is the part no other submission will have, so give it screen time.

Before any finding reaches the student, it is argued:

```
Tax agent          Claim      "FICA withheld from an exempt F-1 student. $440.64 across 8 paystubs."
   │                           + the exact sentence from IRS Pub 519
   ▼
Auditor            Objection  "Is she actually exempt? Year 3 of 5 — check the arrival date.
   │                            Is the employer a school? Was she on-campus?"
   ▼
Tax agent          Rebuttal   Answers each objection from the student file, in code.
   │
   ▼
Auditor            Verdict    upheld / overturned / needs_more — decided in CODE, not by a model
   │
   ├──────────────► Caseworker   opens the refund case only on "upheld"
   └──────────────► Coordinator  narrates it to the student
```

Four agents, four typed message types ([`Claim`, `Objection`, `Rebuttal`, `Verdict`](../agents/messages.py)),
one decision. **A verdict that is not `upheld` opens no case** — it waits for the student's explicit
OK, and logs why ([`agents/caseworker/agent.py:60`](../agents/caseworker/agent.py)).

Say this on camera: *"The student doesn't see a finding until another agent has tried to kill it."*

---

## 5. The reliability story (bonus criterion, and it's real)

The judges ask for "recovery from failed tool calls." We have one that actually happened.

The voice agent is supposed to report what payroll said through a `log_call_outcome` webhook. During
testing that webhook was misconfigured, so **the call completed, payroll made a real promise, and the
case sat in `contacting_employer` forever.** The failure was silent from the caller's side.

The fix ([`agents/caseworker/call_record.py`](../agents/caseworker/call_record.py)): every 45 seconds
the Caseworker reads Cartesia's *own* record of its calls, matches `dynamic_variables.case_id` back to
the case, has Claude classify the written summary into one of four outcomes, and records it. With
guards:

- A promised date must parse as a real date **and not be in the past**, or it isn't stored.
- Anything Claude is unsure of becomes `stalled` — the outcome that asks a human to follow up, rather
  than claiming a promise nobody made.
- The case is re-read per call, so a redial can't record the same outcome twice.

> *"A real promise shouldn't be lost because a webhook was."*

That is a better reliability answer than a retry loop, and it is one file you can open on camera.

---

## 6. Shot list — 4 minutes

Record in these blocks. Don't try for one take.

### 0:00–0:20 · The problem

Face to camera, or voiceover over the ASI:One window.

> "Priya is an F-1 student from Pune. She works in the dining hall. Every paycheck, her employer
> withholds Social Security and Medicare tax — and as an F-1 student in her first five years, she's
> exempt. She's lost $440 and has no idea, because she doesn't know the rule exists."

### 0:20–0:40 · Discovery on ASI:One

Screen: ASI:One, searching for the agent.

Show `docket-coordinator` being found, its published README on screen — badges, features, example
queries. Say:

> "Docket is eight Fetch.ai uAgents, registered on Agentverse. This one speaks the Agent Chat
> Protocol, so the whole thing runs inside ASI:One."

### 0:40–1:30 · Intent → the agents work

Type into ASI:One:

```
check my pay
```

Then **cut to the terminal with all eight agents running** while it thinks. The logs are the proof:
Ledger reading, Tax claiming, Auditor objecting, the verdict landing.

Back to ASI:One for the reply: the two findings, **$440.64**, the 24-hour week, and the quoted IRS
clause under each.

> "Eight agents just did that. The Tax agent found it, the Auditor tried to disprove it, and the
> verdict was decided in code. Every number was computed in Python — the model never does arithmetic."

Point at the quote block:

> "And it's not the model's memory of the IRS. That sentence was fetched from irs.gov and checked word
> for word against the stored page before it was allowed on screen."

### 1:30–2:10 · Action — the phone rings

Type:

```
yes, contact payroll
```

**Have the phone in frame.** Let it actually ring. Answer it on speaker and play payroll:

> *Docket:* "Hi, this is an AI assistant calling on behalf of a student at your university, with her
> permission. This call may be recorded. I'm calling about Social Security and Medicare tax withheld
> in error..."
>
> *You, as payroll:* "Let me check… yes, we can refund that. It'll go out November 16th."
>
> *Docket:* "Thank you. I've recorded that as November 16th."

This is the money shot. **Do not cut away from the ringing phone.** Intent to action, on camera, in
one unbroken take.

### 2:10–2:40 · It remembers

Back to ASI:One:

```
what's wrong?
```

The case now reads *waiting on payroll*, with the promised date. Show the dashboard call log if you
want a second angle.

> "The call outcome went back into the shared file. The case is open, with a follow-up date. That is
> the difference between a chatbot and a caseworker."

Optionally show the recovery (§5) in one line:

> "And if the webhook reporting that call had failed, the Caseworker reads Cartesia's own call record
> 45 seconds later and recovers it. We know, because that's exactly what happened to us."

### 2:40–3:20 · The rest of the agents

Quick hits, one ASI:One message each:

| Type | Shows |
|---|---|
| `my forms` | **Filer** — Form 8843 filled in, every field with the record it came from, on a review card |
| `anyone else?` | **Organizer** — three other students at the same employer, group invite card |
| `do I need to file Form 8843 if I earned nothing?` | **Researcher (Athena)** — ASI:One agentic research, sources re-fetched and verified |

For the Organizer, say the line that matters:

> "Nobody is counted in the group request until they say yes. An invited student's amount isn't in
> the total and their name isn't in the letter."

### 3:20–4:00 · Close

> "Eight uAgents on Agentverse. The Agent Chat Protocol, so it all happens inside ASI:One. Interactive
> cards for approvals. Real tool execution — a bank, a tax-rules engine, live IRS sources, and an
> outbound phone call.
>
> Claude can answer a question about FICA. It can't notice that *you* are paying it, argue with itself
> about whether it's sure, call your payroll office, and still be chasing it in three weeks.
>
> That's Docket."

---

## 7. Lines worth keeping

- *"Ask Claude and you get a confident answer. Ask Docket and you get the right one, with the clause that proves it."*
- *"The student doesn't see a finding until another agent has tried to kill it."*
- *"Every number is computed in code. The model transcribes and explains; it never decides."*
- *"One student is easy to put off. Four is a payroll configuration error."*
- *"A real promise shouldn't be lost because a webhook was."*

---

## 8. If it breaks on camera

| Breaks | Do |
|---|---|
| ASI:One doesn't reach the Coordinator | Check you're messaging the agent, not ASI:One's own assistant. Start the message with the `@agent1...` handle. |
| An agent shows `mailbox: not connected` | Open its inspector link → Connect → Mailbox → restart that agent. |
| The phone doesn't ring | `.venv/bin/python -m scripts.check_voice` reports the API key, agent id and number. Then `.venv/bin/python -m scripts.call_now` places the call directly. |
| The call happens but nothing is recorded | Wait 45s for the recovery pass, then `.venv/bin/python -m scripts.demo_ready`. If you're impatient, run `record_finished_calls()` yourself. |
| The refund total isn't $440.64 | A paystub was dropped. `.venv/bin/python -m scripts.demo_reset` and check it says 8 paystubs. |
| Everything is wrong | `.venv/bin/python -m scripts.demo_reset` (~1 min) puts it back exactly. |

**No-phone fallback:** set `CARTESIA_SIMULATE=1` and a stand-in payroll call runs through the same
webhooks with no phone. Use it to rehearse. Never use it in the submitted video — if the call isn't
real, don't imply it is.

---

## 9. Submission checklist

- [ ] Devpost submission
- [ ] Registered through the **CalHacks Hackathon ASI:One Submission Agent**
- [ ] Public GitHub repo, run instructions in the README
- [ ] Video shows the workflow **inside ASI:One**, not only the dashboard
- [ ] Agentverse agent names/addresses visible or stated
- [ ] Don't claim the Payment Protocol
