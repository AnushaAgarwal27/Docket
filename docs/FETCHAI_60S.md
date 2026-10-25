# Fetch.ai submission — 60 second video

Record in 4 takes. Nothing here needs a new screen: it is the ASI:One chat, the phone, and the
Agentverse page you already have open.

**Before you hit record**

```bash
.venv/bin/python -m scripts.redo_call      # 1s, case back to awaiting_approval
```

- [ ] 8 agents running, Convex up, phone on the desk with the ringer on
- [ ] New ASI:One chat, **To: docket-coordinator**
- [ ] Browser zoomed ~140% so the text reads on a laptop

---

## 0:00–0:10 · The problem

**Screen:** your face, or the ASI:One chat sitting empty.

> "Priya is an F-1 student. Every paycheck, her employer takes out Social Security and Medicare —
> taxes she's exempt from. She's lost $440 and has no idea, because she's never heard of the rule."

---

## 0:10–0:32 · Intent → eight agents → proof

**Screen:** ASI:One. Type:

```
check my pay
```

Let the reply land. Don't talk over the first two seconds.

> "Eight Fetch.ai uAgents on Agentverse, talking over the Agent Chat Protocol. The Tax agent found
> it. The Auditor tried to disprove it. The verdict was decided in code."

Point at the quote under the finding:

> "And that's not the model remembering the IRS. That sentence was fetched from irs.gov and checked
> word for word before it was allowed on screen."

**Scroll to the approval card.** This is your Interactive Cards moment — leave it on screen.

---

## 0:32–0:50 · Action: the phone rings

**Screen:** the card, with the phone in frame.

Press **Approve** on the card (or type `yes, contact payroll`).

**Let it ring. Answer on speaker.**

> *Docket:* "Hi, this is an AI assistant calling on behalf of a student at your university, with her
> permission..."
>
> *You, as payroll:* "Yes, we can refund that. It'll go out November 16th."

This is the whole submission. **Do not cut away from the ringing phone.**

---

## 0:50–1:00 · Close

**Screen:** cut to the Agentverse **My Agents** page, all 8 listed, Active · ASI Available.

> "Eight agents, all on Agentverse, all reachable in ASI:One. Claude can answer a question about
> FICA. It can't notice that *you're* paying it, argue with itself about whether it's sure, and
> call your payroll office.
>
> That's Docket."

---

## If you have 20 spare seconds

Drop them in after the call, before the close:

```
my forms        →  the Filer's Form 8843, filled, with the record behind each field
anyone else?    →  the Organizer: three other students at the same employer
```

Say the line that lands:

> "Nobody is counted in the group request until they say yes."

---

## Don't claim

- The Payment Protocol. Not built.
- That Docket files with the IRS. It prepares forms; it never files.
- That the call is autonomous. Nothing is dialled without her approval.

## If something breaks mid-take

| | |
|---|---|
| Wrong state | `.venv/bin/python -m scripts.redo_call` — 1s, go again |
| Phone doesn't ring | `.venv/bin/python -m scripts.call_now` |
| Call happened, nothing recorded | wait 45s, then `.venv/bin/python -m scripts.demo_ready` |
| Reply never arrives in ASI:One | agents need `DOCKET_LOCAL_ROUTING=1` |
