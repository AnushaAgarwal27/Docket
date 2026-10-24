![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)
![tag:hackathon](https://img.shields.io/badge/hackathon-5F43F1)

# Docket: a caseworker for F-1 students

Docket checks an international student's paychecks for money they are losing without knowing it,
proves each problem with the exact sentence from an official source, and follows up until it is fixed.

## Try it
- **check my pay**: reads your paystubs and flags problems, each with the IRS or federal-regulation clause behind it
- **am I paying tax I shouldn't?**: any wording works
- **what's wrong?**: your open issues and where each case stands
- **what do I need to do for next tax season?**: your year count, last year's filings, and what's due
- **yes** / **no**: approve or decline contacting payroll for a refund

Docket also messages you first: when new paystubs arrive and it notices a problem, and when a refund lands in your account.

## What it checks
- Social Security and Medicare withheld from an F-1 student in their first 5 calendar years
- Weeks over the 20-hour on-campus limit while school is in session
- A missing Form 8843

## How it works
Docket is four Fetch.ai uAgents that react to each other through typed messages and a shared student file:
- **Coordinator** (this agent) talks to you over the chat protocol.
- **Ledger** reads paystubs and bank deposits, and tells Tax when new paystubs land.
- **Tax** runs the rules in code and tells the Coordinator what it found.
- **Caseworker** opens a refund case, drafts the request, and has payroll called only after you say yes.

Rules and math run in code. Claude reads what you type and explains the findings, and code rejects any
reply with a number not in your records or a quote not word for word in the official source.

## Limits
Synthetic demo data only. Every flag says "likely". This is not tax advice; confirm with your international
student office. On calls, Docket says it is an AI acting with your permission and never pretends to be you.
