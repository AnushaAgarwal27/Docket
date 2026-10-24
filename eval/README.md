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

## Running it

```bash
.venv/bin/python -m eval.run --docket-only   # rules engine only, no API calls
.venv/bin/python -m eval.run                 # both arms: 25 plain-Claude answers + 25 grader calls
```

Docket runs the rules engine with every quote checked against the stored sources in Convex.
Plain Claude gets only the student's facts and the question. A grader call (same model, low effort)
reads each free-text answer and records which issues it raised, its FICA amount, and any clause it
quoted; code checks those quotes word for word against the same sources. A profile is correct when
the issues raised match `expected` exactly. Results land in `eval/results/` (not committed).
