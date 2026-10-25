![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)
![tag:hackathon](https://img.shields.io/badge/hackathon-5F43F1)

# Docket: paycheck and tax checker for F-1 international students

Docket checks an F-1 international student's paystubs for money they are losing without knowing it:
Social Security and Medicare (FICA) tax withheld while they are exempt, weeks over the 20-hour on-campus
work limit, and a missing Form 8843. Every finding comes with the exact sentence from the IRS or federal
regulation that supports it, and Docket helps get the refund from payroll, with your approval.

## Who it is for
F-1 (and J-1) international students with an on-campus job (dining hall, library, TA, research assistant)
in their first five calendar years in the United States, and the international student offices that help them.

## Key features
- **FICA refund check**: finds Social Security and Medicare tax withheld from an exempt F-1 student, as separate findings, with the total in dollars and cents
- **20-hour limit check**: flags weeks over 20 hours of on-campus work while school is in session (breaks excluded)
- **Form 8843 reminder**: tells you whether you need Form 8843 and when it is due
- **Proof, word for word**: every finding quotes the official source (IRS Publication 519, 8 CFR 214.2, the IRS Form 8843 page), checked in code against the stored text
- **Refund request**: drafts the request to payroll and contacts payroll only after you approve
- **Follows up**: tells you when the refund lands in your bank account and closes the case
- **Next tax season**: your calendar-year count, what you filed last year, and what is due this year

## Example queries
```
check my pay
am I paying Social Security tax I shouldn't as an F-1 student?
did I work over 20 hours a week on campus?
do I need to file Form 8843 this year?
what do I need to do for next tax season?
```
Then reply **yes** to let Docket contact payroll about the refund, **no** to hold off, or **why?** to see the reasoning.

## How it works
Docket is five Fetch.ai uAgents that work together. This Coordinator talks to you over the chat protocol;
the Ledger reads paystubs and bank deposits, the Tax agent runs the rules in code, the Auditor argues the
employer's side before any finding reaches you, and the Caseworker handles the refund case. All math and
decisions are done in code; Claude only reads paystubs and phrases explanations.

## Limitations
- Not tax or immigration advice. Every finding says "likely": confirm with your school's international student office.
- Does not answer work-eligibility, CPT, OPT or internship questions; those go to your international office.
- Never files anything with the IRS, and never contacts payroll without your explicit approval.
- Demo build with synthetic data (a sample student, Priya); it runs only while the team's agents are online.

## Credits
Built at Cal Hacks 13.0 by Anusha, Rhianna and Soham.
