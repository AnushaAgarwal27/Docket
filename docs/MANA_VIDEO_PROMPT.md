You are making the 3-minute main demo video for **Docket**, our Cal Hacks 13.0 project, **using the Docket Pocket app we built here in Mana as the product on screen**. You know the idea and the app already. This prompt gives you everything else: the real numbers, our user research, exactly what each prize track's judges look for and where that appears, a timed script, and the files to use. Follow it closely. Each track's judges watch for their own criteria, so every track below must be visibly covered. (Fetch.ai also gets its own separate video, so here it gets the essentials, not the deep dive.)

## Output

- One video, **3:00 max**, 16:9, 1080p, plus a **2:00 cut** (what to drop is at the end).
- Voiceover: warm, calm, plain English. No hype words ("revolutionary", "seamless", "game-changing").
- Burned-in captions for every spoken line, and **subtitles on the phone call**.
- A small lower-third **track tag** whenever a sponsor's tool or criterion is on screen, e.g. "Fetch.ai · 8 agents on Agentverse".
- Look: match the Docket Pocket app's own design (its colors, type and components), so the video and the app feel like one product. Green for money recovered, orange for objections.
- **Every product moment is a real Docket Pocket screen**, shown in a phone or browser frame. Don't draw fake UI and don't use screenshots from anywhere else.
- Say "Priya is a synthetic student; the survey is real" once, early.

## The product in one sentence

Docket is an AI caseworker for international students: it notices money they're losing without knowing it, proves it with the IRS's own words, calls payroll with their permission, and follows up until the money is back.

## Our real user research (the Microsoft and Anthropic tracks need this)

**Survey of 65 students** we reached, anonymous, one page:
- 58.5% on F-1, about 3% on J-1. 56.9% work or have worked on campus.
- **73.8% didn't know** F-1 students are usually exempt from Social Security and Medicare tax for 5 years (55.4% "no", 18.5% "not sure").
- **81.5% have never checked a paystub** for Social Security or Medicare.
- **Only 15.4% filed Form 8843** last year, which every F-1 student must file. 29.2% didn't know they had to.
- Problems they've actually had: **25 (38.5%) didn't know they had to file Form 8843**, 12 had CPT/OPT problems, 10 had trouble opening a bank account, 9 missed a tax-treaty benefit, 9 had trouble getting a Social Security number, **8 had Social Security or Medicare wrongly withheld**, and 8 got scam calls.

**Waitlist: 11 students signed up** saying they'd use Docket, all on F-1, from Penn State, Villanova and SFBU.

Present these as "students we surveyed", not as a national statistic.

## The demo story (keep every number exact)

- **Priya Sharma** (synthetic), F-1 from Pune, India. Arrived **Aug 15, 2024**, so 2026 is **calendar year 3 of 5**. Works at **University Dining Services**, **$18/hour**.
- Payroll withheld Social Security and Medicare anyway: **$55.08 a paycheck × 8 = $440.64** (**$357.12** Social Security + **$83.52** Medicare).
- One week she worked **24 hours**, over the **20-hour** on-campus limit. That's a second finding, about her visa status, not money.
- The proof, from **IRS Publication 519**: "Social security and Medicare taxes are not withheld from pay for the work unless the student is considered a resident alien."

## The 8 Fetch.ai agents

Coordinator (the one she talks to, in ASI:One) · Ledger (paystubs and bank) · Tax agent, the Advocate (rules in code, argues her side) · Auditor (argues payroll's side and decides the verdict in code) · Caseworker (case, approval, the call, follow-up) · Researcher (verified answers) · Organizer (spots the same problem across students at one employer) · Filer (fills in forms from her records, submits only what she approves).

**The Hearing**: before she sees anything, the Tax agent claims the money, the Auditor raises 4 objections, the Tax agent answers, and code rules:
- **Contractor work?** Overruled.
- **Past 5 years?** Overruled: she's in year 3 of 5.
- **A different exemption?** Overruled.
- **Can Medicare be recovered?** Sustained.

Verdict: **"Claim stands, with a condition"**, so Priya decides.

## Every track: what its judges look for, and where we show it

| Track | What judges look for | Where it appears | Line to say |
|---|---|---|---|
| **Microsoft, Built for the Real World** | Customer understanding, measurable usefulness, a path to production, responsible design, end-to-end function | Survey charts (0:12), the full flow (0:30–2:10), responsible-design beat and the waitlist (2:10–2:40) | "We surveyed 65 students before building. 74% didn't know the exemption exists, and 81% had never checked a paystub." |
| **Fetch.ai** | Agents on Agentverse, Agent Chat Protocol, used through ASI:One, real action, multi-agent work | ASI:One chat, the Hearing, the approval card, Agentverse list | "Eight Fetch.ai agents on Agentverse, all reached from one chat in ASI:One. Two of them argue every finding before the student sees it." |
| **Cartesia** | Voice at the core, clear and natural, works, responsible use | The **real phone call** (1:20–1:50) | "Docket's Cartesia voice agent makes the call she never would. It says it's an AI calling with her permission, and it never mentions her work hours." |
| **Capital One Nessie** | Completeness, creativity, complexity | Her bank account; the refund deposit closing the case (1:50–2:10) | "Her bank account runs on Capital One's Nessie API. When the refund deposit lands, the Ledger matches it, and the case closes on its own." |
| **Anthropic** | A named community, a real problem, it works, thoughtful use of Claude, knowing where it could go wrong | Survey (named community), the quote check, the eval (2:10–2:25) | "Claude reads paystubs and writes explanations. Code does every calculation and every decision, because a wrong number here costs a student money." |
| **Mana.space** | Meaningful use of Mana, plus one moment where Mana changed what we built or how fast | The Mana moment (2:40–2:52) and the end card | See the Mana beat in the script |
| **Convex** | Real Convex features: live queries, functions, file storage, one backend that updates live | The screens updating on their own as the case moves | "Every agent writes to one Convex student file, so every screen updates live." |
| **Apify** | Meaningful use of Apify | The IRS quote check (0:45–1:10) | "Apify fetches the official IRS pages, and code checks every quote against them word for word." |
| **Best People-First Hack** (general prize) | Impact on people | The whole story | No separate line needed |

## Script (3:00)

**0:00–0:12 · Hook**
Visual: the Docket Pocket home or case screen with Priya's $440.64; slow zoom on the amount.
VO: "Priya is an F-1 student working in her campus dining hall. Every paycheck, $55 comes out for taxes she doesn't owe. She's lost $440.64, and she has no idea."
Caption: *Priya is synthetic. Our survey is real.*

**0:12–0:30 · The real problem (Microsoft, Anthropic)**
Visual: the survey charts animate in one at a time: the 73.8% "didn't know", the 81.5% "never checked", the Form 8843 chart, then the issues bar chart with "8 had Social Security or Medicare wrongly withheld" highlighted.
VO: "Before we wrote any code, we surveyed 65 students. Seventy-four percent didn't know this exemption exists. Eighty-one percent had never checked a paystub. You can't search for a problem you don't know you have."
Tags: *Microsoft · customer understanding* · *Anthropic · a named community: international students*

**0:30–0:45 · Notice (Fetch.ai)**
Visual: our ASI:One screen recording: she types "check my pay". Then the animated workflow diagram, with the Docket Pocket screen that shows the agents working (activity, or the finding appearing).
VO: "Priya opens ASI:One and types: check my pay. Eight Fetch.ai agents go to work. One reads her paystubs and her bank. One runs the IRS rules in code."
Tag: *Fetch.ai · 8 agents on Agentverse · Agent Chat Protocol*

**0:45–1:10 · The Hearing and the proof (Fetch.ai, Anthropic, Apify)**
Visual: the Docket Pocket screen for the Hearing or the finding: the objections, the IRS quote stamped "ADMITTED", then the verdict "Claim stands, with a condition".
VO: "Before she sees anything, two agents argue it. The Auditor objects for payroll: is she past five years? Can Medicare even be recovered? The Advocate answers from her file, and code rules. And the IRS sentence on screen isn't the AI's memory: Apify fetched the page, and code checked it word for word."
Tags: *Fetch.ai · the Hearing* · *Apify · official sources* · *Anthropic · Claude writes, code decides*

**1:10–1:20 · Approve (Fetch.ai Interactive Cards, responsible design)**
Visual: the approval moment: the ASI:One review card from our recording, and/or the Docket Pocket screen where she approves.
VO: "Nothing happens without her yes."
Tag: *Fetch.ai · ASI:One Interactive Cards*

**1:20–1:50 · The real call (Cartesia)**
Visual: our **real phone call recording**, phone in frame, with subtitles. Then the Docket Pocket screen showing the logged call: who answered, the promised date and the reference number.
VO before the call: "Docket's Cartesia voice agent calls payroll."
Play 15–20 seconds of the call: Docket introduces itself as an AI calling with her permission, payroll agrees to refund, and Docket confirms the date.
VO after: "It said it was an AI, never pretended to be her, and never mentioned her work hours, because payroll's slice of her file doesn't contain them. The promise is logged."
Caption: *A teammate plays the payroll office.*
Tag: *Cartesia · voice agent*

**1:50–2:10 · Remember (Nessie, Convex)**
Visual: the Docket Pocket screens for the money: watching the bank for $440.64, then the deposit matched, then the case closed with "Recovered $440.64".
VO: "Docket doesn't stop at a promise. The refund lands in her Capital One account. The Ledger matches it, the case closes, and Docket tells her, without being asked. Every step is one row in a shared Convex file, so every screen updates live."
Tags: *Capital One Nessie* · *Convex · live student file*

**2:10–2:25 · Proof and responsibility (Anthropic, Microsoft)**
Visual: title card. **Docket: 25/25 correct, 0 false alarms, 16/16 quotes verified. Plain Claude: 24/25, 1 false alarm.** Then a quick checklist card: "Asks before every call · Says it's an AI · Never shares her hours · Every finding says 'likely' · Not tax advice".
VO: "On 25 synthetic students, plain Claude told one student he was owed money he wasn't. Docket got all 25 right and verified every quote. And it's built to be careful: it asks before every call, says it's an AI, and tells students to confirm with their international office."
Tags: *Anthropic · eval* · *Microsoft · responsible design*

**2:25–2:40 · Path to production (Microsoft)**
Visual: the waitlist form, then the waitlist counts (11 sign-ups; Penn State, Villanova, SFBU), then Docket Pocket open on a phone.
VO: "Eleven students have already joined the waitlist, from Penn State, Villanova and SFBU. It's live today, and next it goes to international student offices, where one advisor could watch every case at once."
Tag: *Microsoft · path to production*

**2:40–2:52 · The Mana moment (Mana.space)**
Visual: this Mana chat building Docket Pocket, then the finished app.
VO: "[FILL IN, one sentence, true: what Mana changed. For example: 'We built Docket Pocket in Mana, a pocket version a student can open and use, and Mana planned and produced this video.']"
Tag: *Mana.space*

**2:52–3:00 · Close**
Visual: the Docket Pocket "case closed" screen → Docket logo → the app's public Mana link.
VO: "Claude can answer a question. Docket notices the one you didn't know to ask, and follows up until the money is back."
End card: Docket · Built at Cal Hacks 13.0 · Fetch.ai · Cartesia · Capital One Nessie · Anthropic · Microsoft · Convex · Apify · Mana

## Visuals: where each one comes from

- **Product screens: from the Docket Pocket app in this Mana project.** Before building, list every screen the app has and match each script beat to one. If a beat has no matching screen, tell me which; don't invent one.
- **Our uploads:**
  - The survey charts and the waitlist form.
  - The ASI:One chat recording ("check my pay", the Hearing, the cards, "yes").
  - The real phone call recording.
  - The Agentverse list of our 8 agents.
- **The workflow diagram:** you draw it, animated, in the app's style.

## Never say or show

- That Docket files with the IRS. It prepares forms and never files.
- That anyone is called without approval. Every call follows the student's yes.
- That it's tax or immigration advice. Show "Confirm with your school's international office" once.
- Survey numbers as national statistics. Always say "students we surveyed".
- Any survey respondent's name, email or individual answer. Show charts and counts only.
- The Fetch.ai Payment Protocol. Not built.

## The 2:00 cut

Drop, in this order:
1. The Mana screen recording. Keep its tag on the end card and one line in the close.
2. The path-to-production beat. Fold "11 students joined the waitlist" into the survey beat.
3. The eval card. Keep the responsibility line.

Never cut the survey, the Hearing, the approval, the real call, or the refund landing.
