![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)
![tag:hackathon](https://img.shields.io/badge/hackathon-5F43F1)

# Docket Organizer: the students with the same problem, asking together

One student asking payroll to fix one paycheck is easy to put off. Four students at the same employer
with the same finding is a payroll configuration error, and the fix is the same for all of them. This
agent notices that pattern and runs the combined request. It is part of Docket, a caseworker for F-1
international students; students talk to Docket through the **docket-coordinator** agent in ASI:One.

## Key features
- Pattern is computed from flags the rules engine wrote, against the employer on the paystubs the rule actually hit on
- Every affected student is asked individually, and nobody is in the request until they say yes
- The combined total is recomputed from joined members only — an invited student's amount is never counted
- Joining never pauses, merges or weakens the student's own case; declining costs her nothing
- No student learns anything about another: the invitation gives a count and an employer, never a name or another person's amount
- A standing preference (always join / never join / ask me) can answer for her

## Usage
Not chatted with directly. Ask **docket-coordinator** in ASI:One; if a group case applies to you, it
will ask whether you want to join. You can also answer on Docket's student phone line or on the dashboard.

## Limitations
Finds patterns only among students already on Docket. Not legal advice, and not a class action:
it is one letter and one phone call sent on behalf of the students who opted in.

## Credits
Built at Cal Hacks 13.0 by Anusha, Rhianna and Soham.
