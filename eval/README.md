# Eval: plain Claude vs Docket

34 synthetic students with known answers, in `profiles/`. Regenerate with `python -m eval.make_profiles`.

| Group | Count | Expected |
|---|---|---|
| `exempt_withheld` | 8 | `FICA_EXEMPT_F1` with the total withheld |
| `sixth_year_plus` | 4 | nothing (withholding is correct from calendar year 6) |
| `clean` | 4 | nothing |
| `over_20` | 5 | `ONCAMPUS_20_HOURS`, except the winter-break week |
| `no_income_8843` | 4 | `FORM_8843_ANNUAL` |
| `j1_scholar` | 2 | `FICA_EXEMPT_F1` in year 2; nothing in year 3 (2-year exemption) |
| `contractor` | 1 | `FICA_EXEMPT_F1`, basis `f1_nra_exempt`, student exception ruled out |
| `mismatch` | 1 | `FICA_EXEMPT_F1`, Social Security at medium confidence |
| `wrong_form` | 1 | `WRONG_TAX_FORM` warning |
| `unknown_visa` | 1 | nothing, with the reason |
| `opt` | 3 | `OPT_UNEMPLOYMENT` at 86 and 132 days; nothing at 16 |

Each file: `profile`, `paystubs` and `schoolCalendar` (the student's facts), `asOf` (today's date for the run), and the answer key in `expected`, `why` and `group`.

For the plain-Claude run (eval runner, Person 1), paste only `profile`, `paystubs`, `schoolCalendar` and `asOf`, never `expected`, `why` or `group`, then ask: "Is anything wrong with this student's pay or filings?"

The answer key was written by hand from the rules; `tests/test_eval_profiles.py` checks the rules engine agrees on all 34.

## Running it

```bash
.venv/bin/python -m eval.run --docket-only   # rules engine only, no API calls
.venv/bin/python -m eval.run                 # both arms: one plain-Claude answer + one grader call per profile
```

Docket runs the rules engine with every quote checked against the stored sources in Convex.
Plain Claude gets only the student's facts and the question. A grader call (same model, low effort)
reads each free-text answer and records which issues it raised, its FICA amount, and any clause it
quoted; code checks those quotes word for word against the same sources. A profile is correct when
the issues raised match `expected` exactly. Results land in `eval/results/` (not committed).

`python -m eval.score` reports Docket as caught / total with false flags (`--stand-in` runs without downloaded pages).
