# The main demo video

The overall submission video: 3 minutes, all five sponsors, one story.

For the Fetch.ai track video, see [`DEMO_FETCHAI.md`](DEMO_FETCHAI.md). This one is the general
Devpost video — judges who don't care which SDK did what, only whether it works.

---

## The one idea

**Docket notices money you didn't know you were losing, proves it with the actual law, calls your
employer to get it back, and keeps chasing until it lands.**

Everything in the video serves that sentence. If a shot doesn't, cut it.

The structure is four words, and the demo hits them in order:

| | |
|---|---|
| **Notice** | reads her paystubs and finds $440.64 she never knew about |
| **Prove** | the exact IRS sentence, fetched and checked word for word |
| **Act** | calls payroll, on camera, with her approval |
| **Remember** | the case stays open for weeks until the refund lands |

---

## Who Priya is

Say enough that the stakes land, and no more.

> Priya Sharma, F-1 from Pune. Arrived August 2024, so she's in year 3 of 5. CS sophomore, works
> on-campus at dining services, $18/hour. Her parents send rupees for rent.

The fact that does the work: **F-1 students are exempt from Social Security and Medicare tax for
their first five calendar years, and employers withhold it anyway.** She's lost $55 a paycheck for
eight paychecks and has never heard of the rule.

All data is synthetic.

---

## Setup

```bash
.venv/bin/python -m scripts.demo_reset   # ~1 min — clean state, 8 paystubs, $440.64, case open
./scripts/run_agents.sh                  # all eight agents
npm run dashboard                        # http://localhost:5173
```

**Before you record:**

- [ ] `.venv/bin/python -m scripts.demo_ready` → **$440.64**, 8 paystubs
- [ ] Dashboard open on the **Overview** tab, browser zoomed so the feed is readable on a phone
- [ ] ASI:One open in a second window, `docket-coordinator` answering
- [ ] Phone (**+1 925 967 7432**) on the desk, ringer on
- [ ] `CARTESIA_SIMULATE` unset — the call must be real

Screen layout that reads best: **ASI:One on the left, dashboard activity feed on the right.** The feed
lighting up while she's typing is the shot that sells the multi-agent story without you explaining it.

---

## 3-minute script

### 0:00–0:20 · Hook

Over her first paystub, or straight to camera.

> "Priya is an F-1 student. She works in her university dining hall. Every two weeks, $55 comes out of
> her paycheck for Social Security and Medicare — taxes that, as an F-1 student in her first five
> years, she is exempt from.
>
> She's lost $440. She has no idea, because she's never heard of the rule. You can't Google a problem
> you don't know you have."

### 0:20–0:50 · Notice

ASI:One:

```
check my pay
```

Let the **activity feed on the right** run while it works. Don't talk over the first two seconds —
let the rows land.

> "Eight Fetch.ai agents just went to work. One read her paystubs. One ran the tax rules. One argued
> the employer's side. Every row you're seeing is an agent writing to a shared file that the others
> react to."

The reply: **$440.64 across 8 paystubs**, and a second finding — a 24-hour week against the 20-hour
on-campus limit.

> "Two findings. She asked about her pay; she also found out she's over the work-hours limit, which
> is a status problem, not a money one."

### 0:50–1:20 · Prove

Point at the quoted clause under the finding.

> "This is the part that matters. That's not the model remembering what the IRS says. That sentence
> was fetched from irs.gov, stored, and checked word for word before it was allowed on screen. If the
> quote doesn't match the stored page, the finding doesn't ship."

If you have 10 spare seconds, show the rejection live in a terminal:

```bash
python -m rules.demo_rejection
```

> "A made-up clause gets rejected and logged. The real one passes. Same check, every time."

### 1:20–2:00 · Act

ASI:One:

```
yes, contact payroll
```

**Phone in frame. Let it ring. Answer on speaker.**

> *Docket:* "Hi, this is an AI assistant calling on behalf of a student at your university, with her
> permission. This call may be recorded..."
>
> *You, as payroll:* "Yeah, I see it. We can refund that — it'll go out November 16th."
>
> *Docket:* "Thank you, I've got November 16th."

Then, over the dashboard updating:

> "It said it was an AI. It never pretended to be her. And it never mentioned the hours problem —
> payroll's slice of her file doesn't contain it, so there's nothing to leak."

That last line is the privacy architecture in one sentence. Keep it.

### 2:00–2:30 · Remember

Click **Simulate 2 weeks** on the dashboard.

> "Two weeks later, the refund deposit lands in her bank. The Ledger agent matches it to the open
> case, and the case closes on its own. Nobody checked. Nobody remembered to follow up. That's the
> difference between an answer and a caseworker."

Watch the case go to **refund received → closed** live.

### 2:30–3:00 · Close

Either the eval slide, or the group feature. **Pick one** — there isn't room for both.

**Option A, the eval** (stronger with technical judges):

> "We tested plain Claude against Docket on 25 student profiles. Claude answers the question you ask.
> Docket finds the problem you didn't know to ask about, and sources every answer."

**Option B, the group** (stronger emotionally):

```
anyone else?
```

> "Three other students at the same employer have the identical problem. Docket asks each of them
> whether they want to join — and nobody is counted until they say yes. One student is easy to put
> off. Four is a payroll configuration error."

Final line either way:

> **"Claude can answer a question. It can't notice the one you didn't know to ask."**

---

## Where each sponsor shows up

Make sure every one of these is visible at least once. The judges are looking for their own tool.

| Sponsor | On screen at | What to say if you name it |
|---|---|---|
| **Fetch.ai** | 0:20 — ASI:One + the feed | "Eight uAgents on Agentverse, talking over the Agent Chat Protocol." |
| **Anthropic / Claude** | 0:50 — the quote, and the rejection | "Claude reads the paystubs and writes the explanations. Code does all the math and every decision." |
| **Cartesia** | 1:20 — the phone ringing | "A real outbound call that reads the live case file mid-call." |
| **Convex** | throughout — the feed updating | "The shared student file. Every panel is a live query; nothing is refreshed." |
| **Capital One Nessie** | 2:00 — the refund landing | "Her actual bank. The refund deposit is what closes the case." |
| **Apify** | 0:50 — alongside the quote | "Fetches the official IRS and eCFR pages, and hashes them so we notice when the law page changes." |

---

## Shooting notes

- **Record in blocks, not one take.** The phone call is the only shot that must be continuous.
- **Don't narrate the UI.** Nobody needs "and now I'll click here." Say what it means.
- **Let the feed breathe.** Two seconds of silence while rows land is more convincing than talking.
- **Zoom the browser to ~140%.** Most judges watch on a laptop in a noisy room, some on a phone.
- **Subtitle the phone call.** Speakerphone audio is the first thing to go unintelligible.
- **Say "synthetic data" once**, early. It buys trust and costs two seconds.

### Don't claim

- That Docket files anything with the IRS. It prepares forms; it never files.
- That the call is autonomous. Nothing is dialled without the student's explicit approval.
- The Fetch.ai Payment Protocol. Not implemented.
- That it's tax or immigration advice. Every finding says "likely" and points to the international
  student office — keep that on screen at least once.

---

## If it breaks mid-shoot

| Breaks | Do |
|---|---|
| Any wrong state | `.venv/bin/python -m scripts.demo_reset` — ~1 min, puts it back exactly |
| Phone doesn't ring | `.venv/bin/python -m scripts.check_voice`, then `.venv/bin/python -m scripts.call_now` |
| Call happened, nothing recorded | Wait 45s for the recovery pass, then `.venv/bin/python -m scripts.demo_ready` |
| Total isn't $440.64 | A paystub was dropped — re-run `demo_reset` and confirm it says 8 paystubs |
| Dashboard blank | A WebGL failure is caught by a boundary; reload. The 3D tab is the only part that needs it. |

---

## The 2-minute cut

If the submission caps at 2 minutes, drop in this order:

1. The eval/group close (0:30) — end on the refund landing instead
2. The `demo_rejection` terminal shot (0:10)
3. The second finding, the 20-hour flag (0:10)

Never cut: the phone ringing, or the quoted clause. Those are the two things nobody else will have.
