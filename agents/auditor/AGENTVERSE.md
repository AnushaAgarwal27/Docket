![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)
![tag:hackathon](https://img.shields.io/badge/hackathon-5F43F1)

# Docket Auditor: the employer's side of every F-1 tax finding

Before a finding reaches the student, the Auditor argues the other side: every reason the claim might be
wrong. The verdict is decided in code, and the Auditor can win, for example when a student is in their 6th
calendar year and the withholding is correct. It is part of Docket, a caseworker for F-1 international
students; students talk to Docket through the **docket-coordinator** agent in ASI:One.

## Key features
- Deterministic objection checks: employer is a contractor, a different student exemption may apply, calendar-year boundary, Medicare recovery uncertain, school in session, missing visa or arrival facts
- Verdicts: upheld, downgraded (an exception may apply, so the student decides), needs a human (facts missing), or defeated (no claim)
- A downgraded or needs-a-human verdict means no refund case is opened without the student's explicit OK
- Every objection and verdict is stored, so the student can ask "why?" later

## Usage
Not chatted with directly; ask **docket-coordinator** in ASI:One, then `why?` to replay the Hearing.

## Limitations
Argues only from the facts in the student file. Not tax or immigration advice.

## Credits
Built at Cal Hacks 13.0 by Anusha, Rhianna and Soham.
