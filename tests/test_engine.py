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


from rules.download_sources import page_text
from rules.quote_checker import source_status

PUB_519_HTML = """<html><head><script>var x = 1;</script></head><body><h2>Students and exchange visitors</h2>
<p>Social security and Medicare taxes are not withheld from pay for the work unless the student is
considered a resident&nbsp;alien.</p></body></html>"""


def test_pub_519_sentence_verified_against_downloaded_page():
    sources = {**sources_with_rule_quotes(), "FICA_EXEMPT_F1": page_text(PUB_519_HTML)}
    fica = run(sources=sources).flags[0]
    assert fica["ruleId"] == "FICA_EXEMPT_F1" and fica["sourceStatus"] == "verified"


def test_downloaded_page_without_the_sentence_produces_no_flag():
    page = page_text(PUB_519_HTML.replace("are not withheld", "may be withheld"))
    out = run(sources={**sources_with_rule_quotes(), "FICA_EXEMPT_F1": page})
    assert "FICA_EXEMPT_F1" not in [f["ruleId"] for f in out.flags]
    assert any(a["action"] == "flag_rejected" and a["ruleId"] == "FICA_EXEMPT_F1" for a in out.activity)


def test_allow_list():
    assert source_status("https://www.irs.gov/publications/p519") == "verified"
    assert source_status("https://www.uscis.gov/working-in-the-united-states") == "verified"
    assert source_status("https://internationaloffice.berkeley.edu/students") == "verified"
    assert source_status("https://irs.gov.example.com/p519") == "unverified"
    assert source_status("https://www.ecfr.gov/current/title-8/section-214.2") == "verified"
    assert source_status("https://www.studyinthestates.example.org/f1") == "unverified"


def test_off_list_source_still_flags_but_is_marked_unverified():
    rules = [{**r, "source_url": "https://blog.example.com/f1-hours"} if r["id"] == "ONCAMPUS_20_HOURS" else r
             for r in load_rules()]
    flags = {f["ruleId"]: f for f in run(rules=rules).flags}
    assert flags["ONCAMPUS_20_HOURS"]["sourceStatus"] == "unverified"
    assert flags["FICA_EXEMPT_F1"]["sourceStatus"] == "verified"


def test_not_triggered_rows_say_why():
    reasons = {a["ruleId"]: a["detail"] for a in run().activity if a["action"] == "rule_not_triggered"}
    assert reasons["FORM_8843_ANNUAL"] == "Form 8843 for 2025 already filed"
    assert reasons["WRONG_TAX_FORM"] == "no tax software reported"
