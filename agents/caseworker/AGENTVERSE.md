![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)
![tag:hackathon](https://img.shields.io/badge/hackathon-5F43F1)

# Docket Caseworker: FICA refund cases for F-1 students, from approval to deposit

The Caseworker turns a verified finding into a refund case and follows it until the money is back: it drafts
the request to payroll, waits for the student's approval, has payroll called, writes a follow-up letter if
payroll stalls, and closes the case when the refund deposit lands. It is part of Docket, a caseworker for F-1
international students; students talk to Docket through the **docket-coordinator** agent in ASI:One.

## Key features
- Case states: open, awaiting approval, contacting payroll, awaiting response, refund received, closed; IRS escalation (Forms 843 and 8316 checklist) if payroll refuses
- Nothing is sent and no one is called without the student's explicit approval
- Payroll call through a Cartesia voice agent that says it is an AI acting with the student's permission
- Refund request letter as a PDF, using only the amounts the rules computed and the verified quote

## Usage
Not chatted with directly; ask **docket-coordinator** in ASI:One and reply `yes` to approve contacting payroll.

## Limitations
Demo payroll is a teammate's phone; real outbound calls carry consent and calling-hours rules. Not tax advice.

## Credits
Built at Cal Hacks 13.0 by Anusha, Rhianna and Soham.
