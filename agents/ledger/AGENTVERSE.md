![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)
![tag:hackathon](https://img.shields.io/badge/hackathon-5F43F1)

# Docket Ledger: paystub and bank-feed reader for F-1 students

The Ledger turns a student's paystub PDFs and bank transactions into one clean, checked record that the
other Docket agents work from. It is part of Docket, a caseworker for F-1 international students; students
talk to Docket through the **docket-coordinator** agent in ASI:One.

## Key features
- Reads paystub PDFs (Claude copies what is printed; code parses every number into integer cents)
- Checks each paystub in code: Social Security 6.2% and Medicare 1.45% of gross, hours x rate = gross, net matches a deposit
- Pulls deposits and purchases from the bank feed (Capital One Nessie sandbox), with no duplicates on re-poll
- Tells the Tax agent as soon as new paystubs land, and tells the Coordinator when a refund deposit matches an open case
- Stores each original paystub PDF so every finding has a receipt

## Usage
Not chatted with directly. It runs on a timer and messages the other Docket agents; ask **docket-coordinator** instead, e.g. `check my pay`.

## Limitations
Synthetic demo data only. Mismatches are reported as warnings, never silently fixed. Not tax advice.

## Credits
Built at Cal Hacks 13.0 by Anusha, Rhianna and Soham.
