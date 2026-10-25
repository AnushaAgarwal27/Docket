You are producing the 3-minute demo video for **Docket**, our Cal Hacks 13.0 project. You already know the idea. This prompt adds what you don't have: exactly how each sponsor track must appear on screen, the real numbers, the script, and the screenshots to use. Follow it closely. Every sponsor's judges watch for their own tool, so each one must be visible and named at least once.

## Output

- One video, **3:00 max**, 16:9, 1080p. Plus a **2:00 cut** (what to drop is at the end).
- Voiceover: warm, calm, plain English. No hype words ("revolutionary", "seamless", "game-changing").
- Burned-in captions for every spoken line.
- A small lower-third **sponsor tag** whenever a sponsor's tool is on screen (e.g. "Fetch.ai · 8 uAgents on Agentverse").
- Look: cream and beige paper, dark ink text, one green accent for money recovered and orange for objections. These match the game's colors.
- Say "all data is synthetic" once, early.

## The product in one sentence

Docket notices money an international student didn't know she was losing, proves it with the IRS's own words, gets it back with her permission, and follows up until it lands.

## The story (keep every number exact)

- **Priya Sharma**, F-1 student from Pune, India. Arrived **Aug 15, 2024**, so 2026 is **calendar year 3 of 5**. CS sophomore. Works at **University Dining Services**, **$18/hour**.
- F-1 students are exempt from Social Security and Medicare tax for their first 5 calendar years. Payroll withheld it anyway: **$55.08 per paycheck** across **8 paychecks** = **$440.64** (**$357.12** Social Security + **$83.52** Medicare).
- One week she worked **24 hours**, over the **20-hour** on-campus limit. That's a second finding, about her visa status, not money.
- The proof sentence, from **IRS Publication 519**: "Social security and Medicare taxes are not withheld from pay for the work unless the student is considered a resident alien."

## The 8 Fetch.ai agents (name them like this)

1. **Coordinator**: the only agent Priya talks to, in ASI:One.
2. **Ledger**: reads her paystubs and bank account, checks every number, and spots the refund when it lands.
3. **Tax agent (the Advocate)**: runs the IRS rules in code and argues Priya's side.
4. **Auditor**: argues payroll's side, then decides the verdict in code.
5. **Caseworker**: opens the case, waits for her yes, calls payroll, and follows up.
6. **Researcher (Athena)**: answers what her file can't, and keeps only sources that code verified.
7. **Organizer**: notices when several students at one employer have the same problem.
8. **Filer**: fills in her forms from her records, and submits only what she approves.

**The Hearing**: before Priya sees anything, the Tax agent makes the claim, the Auditor objects, the Tax agent answers, and code issues the verdict. In our real run the Auditor raised 4 objections:
- **Contractor work?** Overruled.
- **Past 5 years?** Overruled: she's in year 3 of 5.
- **Different exemption?** Overruled.
- **Can Medicare be recovered?** Sustained.

Verdict: **"Claim stands, with a condition"**, so Priya decides.

## Each sponsor track: what must be on screen and what to say

| Track | Show | Say (one line, word for word) |
|---|---|---|
| **Fetch.ai** (main track) | ASI:One chat with the Coordinator; Agentverse showing the 8 agents online; the Hearing | "Eight Fetch.ai agents on Agentverse, talking over the Agent Chat Protocol. You reach all of them from one chat in ASI:One." |
| **Fetch.ai: Interactive Cards** | The review card in ASI:One with the Approve button | "ASI:One Interactive Cards: the finding, the proof and the approve button, right in the chat." |
| **Anthropic / Claude** | The IRS quote on screen; eval numbers | "Claude reads the paystubs and writes the explanations. Code does every calculation and makes every decision. Claude never invents a rule." |
| **Anthropic: eval** | Title card: **Docket 25/25 correct, 0 false alarms, 16/16 quotes verified. Plain Claude 24/25 and 1 false alarm**: it told a sixth-year student he was owed a refund | "We tested plain Claude against Docket on 25 synthetic students. Claude was confident. Docket was right, and showed its source every time." |
| **Convex** | The dashboard updating on its own; the game reading the same file | "One shared student file on Convex. Every agent writes to it, and every screen updates live. Nothing is refreshed." |
| **Cartesia** | The game's Round 2 (Approved → Dialing → Connected → Outcome) and the call log | "With her yes, Docket's Cartesia voice agent calls payroll. It says it's an AI calling with her permission, and it never mentions her hours." |
| **Capital One Nessie** | Round 3: the refund deposit landing, "+$440.64" | "This is her bank account in Capital One's Nessie sandbox. When the refund deposit lands, the Ledger matches it, and the case closes on its own." |
| **Apify** | The IRS quote with "fetched and checked word for word" | "Apify fetches the official IRS pages. If the law page changes, Docket notices and holds the finding back." |

## Script

**0:00–0:15 · Hook**
Visual: `01-game-title-live-case.png`, slow zoom on "$440.64".
VO: "Priya is an F-1 student working in her university dining hall. Every paycheck, $55 comes out for taxes she doesn't owe. She's lost $440.64, and she has no idea."
Caption: *All data is synthetic.*

**0:15–0:35 · Fetch.ai: the agents**
Visual: Agentverse with the 8 agents online (screen recording), then the ASI:One chat.
VO: "Docket is eight Fetch.ai agents. Priya only ever talks to one, the Coordinator, in ASI:One. She types: check my pay."
Tag: *Fetch.ai · 8 uAgents on Agentverse · Agent Chat Protocol*

**0:35–1:10 · The Hearing (Fetch.ai multi-agent)**
Visual: `02-round1-hearing-card.png`, then the ASI:One Hearing narration (screen recording), then `03-hearing-claim-stands.png`.
VO: "Before she sees anything, two agents argue it. The Tax agent claims the money. The Auditor objects for payroll: is this contractor work? Is she past five years? Can Medicare even be recovered? The Tax agent answers from her file, and code rules: three objections overruled, one sustained. The claim stands, with a condition, so Priya decides."
Tags: *Fetch.ai · the Hearing* and *Anthropic · Claude writes, code decides*

**1:10–1:30 · Prove (Anthropic + Apify)**
Visual: the IRS quote large on screen, with "IRS Publication 519 · checked word for word" stamped "ADMITTED".
VO: "That isn't the AI remembering what the IRS says. Apify fetched the page, and code checked the sentence word for word before it was allowed on screen. If it doesn't match, the finding never ships."
Tags: *Apify* and *Anthropic*

**1:30–1:45 · Approve (Fetch.ai Interactive Cards)**
Visual: the ASI:One review card; Priya replies "yes".
VO: "Nothing happens without her yes."
Tag: *Fetch.ai · ASI:One Interactive Cards*

**1:45–2:10 · Act (Cartesia)**
Visual: `05-round2-call-card.png`, then `06-call-logged.png`. If we give you a real call recording, play 8–10 seconds of it with subtitles instead.
VO: "Docket's Cartesia voice agent calls payroll. It says it's an AI calling with her permission, asks for the refund, and logs what payroll promised: a refund by November 8th. It never mentions her work hours. Payroll's slice of her file doesn't contain them."
Tag: *Cartesia · voice agent*

**2:10–2:35 · Remember (Nessie + Convex)**
Visual: `07-round3-money-card.png`, `08-post-refund-to-bank.png`, `09-deposit-matched.png`, then `10-case-closed.png`. Cut to `11-dashboard-refunded.png`.
VO: "Docket doesn't stop at a promise. The refund lands in her Capital One account. The Ledger matches it to the case, the case closes, and Docket tells her, without being asked. Every step is one row in a shared Convex file, so every screen updates live."
Tags: *Capital One Nessie* and *Convex · live student file*

**2:35–2:50 · Proof it works (Anthropic eval)**
Visual: an eval title card with the numbers from the table.
VO: "We tested plain Claude against Docket on 25 synthetic students. Docket got all 25 right and verified every quote. Plain Claude told one student he was owed money he wasn't."

**2:50–3:00 · Close**
Visual: `10-case-closed.png` → logo → "docket-game.vercel.app".
VO: "Claude can answer a question. Docket notices the one you didn't know to ask, and follows up until the money is back."
End card: Docket · Built at Cal Hacks 13.0 · Fetch.ai · Anthropic · Convex · Cartesia · Capital One Nessie · Apify

## Screenshots to use (uploaded with this prompt)

| File | What it shows |
|---|---|
| `01-game-title-live-case.png` | Game title screen; the "Live" case card selected |
| `02-round1-hearing-card.png` | Round 1 title: "The hearing" |
| `03-hearing-claim-stands.png` | Courtroom: Advocate vs Auditor; banner "Claim stands, with a condition · $440.64 · Priya decides" |
| `04-hearing-verdict.png` | The Judge reading the verdict |
| `05-round2-call-card.png` | Round 2 title: "The call" |
| `06-call-logged.png` | Switchboard; Approved, Dialing, Connected; "Call logged… Promised by Nov 8, 2026" |
| `07-round3-money-card.png` | Round 3 title: "The money" |
| `08-post-refund-to-bank.png` | The "Post the refund to the test bank" step |
| `09-deposit-matched.png` | The Ledger: "Deposit matched to the case" |
| `10-case-closed.png` | End screen: "$440.64 is back with Priya." |
| `11-dashboard-refunded.png` | Live dashboard: Recovered $440.64, case closed |
| `12-dashboard-finding.png` | Live dashboard before the refund: $440.64 withheld in error across 8 paychecks |

Screen recordings we'll add separately: ASI:One chat (`check my pay`, the Hearing, cards, `yes`) and the Agentverse agent list.

## Never say or show

- That Docket files anything with the IRS. It prepares forms; it never files.
- That it calls anyone without approval. Every call follows the student's explicit yes.
- That it's tax or immigration advice. Show "Confirm with your school's international office" once.
- A real phone call, unless we give you a real recording. Otherwise it's the call log only. In the game the call is a rehearsal labelled "Payroll office (rehearsal)", so crop that label or say "rehearsal".
- The Fetch.ai Payment Protocol. Not built.
- Any real student's name or data. Priya is synthetic.

## The 2:00 cut

Drop, in this order: the eval (2:35–2:50), the Apify beat (fold its line into the Hearing), then the Agentverse shot (keep the ASI:One chat). Never cut the Hearing, the approval or the refund landing.
