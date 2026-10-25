![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)
![tag:hackathon](https://img.shields.io/badge/hackathon-5F43F1)

# Docket Tax: F-1 FICA, 20-hour limit and Form 8843 rules engine

The Tax agent applies official rules to an F-1 student's pay and filings, in code, and argues the student's
side (the Advocate) in Docket's Hearing. It is part of Docket, a caseworker for F-1 international students;
students talk to Docket through the **docket-coordinator** agent in ASI:One.

## Key features
- FICA exemption: Social Security and Medicare withheld from an F-1 student in the first five calendar years
- 20-hour on-campus limit while school is in session, using the school calendar (breaks excluded)
- Form 8843 needed, with the deadline
- Shows a finding only if its quote appears word for word in the stored official source (IRS Publication 519, 8 CFR 214.2, IRS Form 8843 page); rejections are logged
- Runs on its own when new paystubs arrive, and answers the Auditor's objections from the facts

## Usage
Not chatted with directly; ask **docket-coordinator** in ASI:One, e.g. `am I paying tax I shouldn't?`.

## Limitations
Every finding says "likely" and points to the school's international office. Not tax or immigration advice.

## Credits
Built at Cal Hacks 13.0 by Anusha, Rhianna and Soham.
