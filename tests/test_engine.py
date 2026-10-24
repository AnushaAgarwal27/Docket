from datetime import date

from seed import demo_data as d
from rules.engine import evaluate, load_rules

AS_OF = date(2026, 10, 24)


def sources_with_rule_quotes():
    """Stand-in for fetched pages: each source contains its rule's quote inside other text."""
    return {r["source_id"]: f"Header text.\n{r['quote']}\nFooter text." for r in load_rules()}


def run(**kw):
    return evaluate(d.PROFILE, d.paystubs(), d.SCHOOL_CALENDAR, AS_OF, kw.pop("sources", sources_with_rule_quotes()), **kw)


def test_priya_gets_exactly_two_flags():
    out = run()
    assert [(f["ruleId"], f["amountCents"]) for f in out.flags] == [("FICA_EXEMPT_F1", 44064), ("ONCAMPUS_20_HOURS", 0)]
    assert {a["action"] for a in out.activity} == {"flag_raised", "rule_not_triggered"}


def test_every_rule_writes_an_activity_row():
    assert len(run().activity) == len(load_rules())


def test_made_up_clause_is_rejected_and_logged():
    out = run(quotes={"FICA_EXEMPT_F1": "F-1 students are exempt from all federal taxes for their first five years."})
    assert [f["ruleId"] for f in out.flags] == ["ONCAMPUS_20_HOURS"]
    rejected = [a for a in out.activity if a["action"] == "flag_rejected"]
    assert rejected[0]["ruleId"] == "FICA_EXEMPT_F1" and rejected[0]["detail"] == "quote not found in stored source"


def test_unfetched_source_means_no_flag():
    out = run(sources={})
    assert out.flags == [] and sum(a["detail"] == "source not fetched" for a in out.activity) == 2
