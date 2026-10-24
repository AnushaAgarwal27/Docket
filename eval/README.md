# Eval: plain Claude vs Docket

25 synthetic students with known answers, in `profiles/`. Regenerate with `python -m eval.make_profiles`.

| Group | Count | Expected |
|---|---|---|
| `exempt_withheld` | 8 | `FICA_EXEMPT_F1` with the total withheld |
| `sixth_year_plus` | 4 | nothing (withholding is correct from calendar year 6) |
| `clean` | 4 | nothing |
| `over_20` | 5 | `ONCAMPUS_20_HOURS`, except the winter-break week |
| `no_income_8843` | 4 | `FORM_8843_ANNUAL` |

Each file: `profile`, `paystubs` and `schoolCalendar` (the student's facts), `asOf` (today's date for the run), and the answer key in `expected`, `why` and `group`.

For the plain-Claude run (eval runner, Person 1), paste only `profile`, `paystubs`, `schoolCalendar` and `asOf`, never `expected`, `why` or `group`, then ask: "Is anything wrong with this student's pay or filings?"

The answer key was written by hand from the rules; `tests/test_eval_profiles.py` checks the rules engine agrees on all 25.
