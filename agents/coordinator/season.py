"""The "next tax season" message: what Priya files for this year, built by code from her profile.

Uses her calendar-year count and last year's filings from the student file, and the existing rule
functions in rules/rules.py (unchanged) for the exemption years and the Form 8843 deadline. Claude
writes none of it. The Form 8843 clause is shown only if it is still word for word in the stored source.
"""
from __future__ import annotations

from datetime import date

from agents.store import query
from rules.engine import load_rules
from rules.quote_checker import check_quote
from rules.rules import EXEMPT_CALENDAR_YEARS, calendar_year_number, needs_8843


def filed(profile: dict, year: int) -> list[str]:
    forms = [f["form"] for f in profile.get("filings") or [] if f["year"] == year]
    if not forms and year in (profile.get("filed8843Years") or []):
        forms = ["8843"]
    return forms


def next_season(profile: dict, paystubs: list[dict], calendar: dict, today: date) -> str:
    tax_year = today.year  # the year she files for next season
    n = calendar_year_number(profile["arrivalDate"], tax_year)
    last_exempt = date.fromisoformat(profile["arrivalDate"]).year + EXEMPT_CALENDAR_YEARS - 1
    lines = [f"Here's your next tax season, for the {tax_year} tax year:"]

    if profile["visa"] not in ("F-1", "J-1") or n > EXEMPT_CALENDAR_YEARS:
        lines.append(f"- {tax_year} is calendar year {n} for you, past the {EXEMPT_CALENDAR_YEARS}-year exempt period, "
                     "so the student rules I check no longer apply. Ask your international student office "
                     "how to file this year.")
        return "\n".join(lines)

    lines.append(f"- {tax_year} is **calendar year {n} of {EXEMPT_CALENDAR_YEARS}** on your F-1, so you are still "
                 f"exempt from Social Security and Medicare tax on campus work. "
                 f"{'This is your last exempt year.' if n == EXEMPT_CALENDAR_YEARS else f'That lasts through {last_exempt}.'}")

    last = tax_year - 1
    done = filed(profile, last)
    lines.append(f"- Last year ({last}) you filed: Form {', Form '.join(done)}." if done
                 else f"- I don't see any forms filed for {last}. If you filed, tell your international student office "
                      "so your record is right; if not, ask them how to catch up.")

    # needs_8843 checks the year before as_of, so ask it as of next January.
    hit = needs_8843({**profile, "filed8843Years": [y for y in profile.get("filed8843Years") or [] if y != tax_year]},
                     paystubs, calendar, date(tax_year + 1, 1, 1))
    if hit:
        wages = " (you had US wages this year)" if hit["hadWages"] else ""
        lines.append(f"- You'll need **Form 8843 for {hit['taxYear']}**, due **{hit['deadline']}**{wages}.")
        rule = next(r for r in load_rules() if r["id"] == "FORM_8843_ANNUAL")
        source = query("sources:getByUrl", {"url": rule["source_url"]})
        if source and check_quote(rule["quote"], source["text"]).ok:
            lines.append(f"\n> {rule['quote']}\n\n— {rule['source_title']}: {rule['source_url']}")
    return "\n".join(lines)
