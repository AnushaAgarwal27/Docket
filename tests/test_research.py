"""Athena: the source check, and what leaves the machine before it.

The source check is the whole claim of this feature — that an answer is research rather than a model
talking. These tests drive it against pages served by a fake session, with no network.
"""
import pytest

from agents.researcher import athena, engine

ANSWER = ("Yes. Contact the employer who withheld the taxes for a refund. If the employer cannot "
          "refund it, file Form 843 with Form 8316.")

IRS_PAGE = ("<html><body><p>If social security or Medicare taxes were withheld in error from pay "
            "that is not subject to these taxes, contact the employer who withheld the taxes for a "
            "refund.</p></body></html>")
UNRELATED_PAGE = "<html><body><p>Campus dining hours are 7am to 9pm during the fall term.</p></body></html>"


class Resp:
    def __init__(self, status=200, text=""):
        self.status_code, self.text = status, text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    """Serves the pages it was given; anything else 404s, like a dead link would."""
    def __init__(self, pages):
        self.pages, self.fetched = pages, []

    def get(self, url, headers=None, timeout=None):
        self.fetched.append(url)
        return Resp(200, self.pages[url]) if url in self.pages else Resp(404, "")


# ---------- the source check ----------

def test_a_page_that_supports_the_answer_is_kept():
    url = "https://www.irs.gov/individuals/international-taxpayers/foreign-student-liability"
    session = FakeSession({url: IRS_PAGE})
    sources = athena.verify_sources(ANSWER, [athena.Source("IRS", url)], session=session)
    assert sources[0].verified is True
    # The excerpt is the run of the answer's own words that was found on the page, so it keeps the
    # answer's casing; the match itself is case-insensitive.
    assert "contact the employer who withheld" in sources[0].excerpt.lower()


def test_a_page_that_does_not_support_the_answer_is_dropped():
    url = "https://example.edu/dining"
    session = FakeSession({url: UNRELATED_PAGE})
    sources = athena.verify_sources(ANSWER, [athena.Source("Dining", url)], session=session)
    assert sources[0].verified is False
    assert sources[0].excerpt == ""


def test_an_unreachable_page_is_dropped():
    session = FakeSession({})  # every fetch 404s
    sources = athena.verify_sources(ANSWER, [athena.Source("Gone", "https://example.gov/missing")],
                                    session=session)
    assert sources[0].verified is False


def test_duplicate_urls_are_fetched_once():
    url = "https://www.irs.gov/p519"
    session = FakeSession({url: IRS_PAGE})
    athena.verify_sources(ANSWER, [athena.Source("a", url), athena.Source("b", url)], session=session)
    assert session.fetched == [url]


# ---------- confidence follows the check, not the engine's tone ----------

def test_confidence_is_high_only_for_a_verified_official_page():
    official = athena.Source("IRS", "https://www.irs.gov/p519", excerpt="x", verified=True)
    other = athena.Source("Blog", "https://example.com/post", excerpt="x", verified=True)
    unverified = athena.Source("IRS", "https://www.irs.gov/p519", verified=False)
    assert athena.confidence_for([official]) == "high"
    assert athena.confidence_for([other]) == "medium"
    assert athena.confidence_for([unverified]) == "low"
    assert athena.confidence_for([]) == "low"


def test_an_answer_with_no_surviving_source_is_low_confidence(monkeypatch):
    """The engine sounded sure; nothing backed it up. That has to come out as low."""
    monkeypatch.setattr(athena, "asi_one_available", lambda: False)
    monkeypatch.setattr(athena, "ask_claude",
                        lambda q, c: ("Definitely yes, guaranteed.",
                                      [athena.Source("Nowhere", "https://example.gov/404")], "test"))
    finding = athena.research("can I?", session=FakeSession({}))
    assert finding.confidence == "low"
    assert all(not s.verified for s in finding.sources)


def test_claude_is_the_fallback_when_asi_one_fails(monkeypatch):
    monkeypatch.setattr(athena, "asi_one_available", lambda: True)
    monkeypatch.setattr(athena, "ask_asi_one",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("502")))
    monkeypatch.setattr(athena, "ask_claude", lambda q, c: (ANSWER, [], "claude-opus-5"))
    finding = athena.research("can I?", session=FakeSession({}))
    assert finding.ok and finding.engine == "claude-opus-5"


def test_both_engines_failing_is_an_error_not_an_answer(monkeypatch):
    monkeypatch.setattr(athena, "asi_one_available", lambda: True)
    monkeypatch.setattr(athena, "ask_asi_one", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("502")))
    monkeypatch.setattr(athena, "ask_claude", lambda q, c: (_ for _ in ()).throw(RuntimeError("no key")))
    finding = athena.research("can I?", session=FakeSession({}))
    assert finding.ok is False and finding.answer == ""


# ---------- what leaves the machine ----------

PROFILE = {"name": "Priya Sharma", "visa": "F-1", "employer": "University Dining Services",
           "school": "Golden Bear University", "employerIsSchool": True}


def test_scrub_removes_name_employer_school_phone_and_email():
    asked = ("Priya Sharma here, my job at University Dining Services at Golden Bear University "
             "took social security. Call me on 555-123-9876 or priya@example.edu")
    out = engine.scrub(asked, PROFILE)
    for secret in ("Priya", "Sharma", "University Dining Services", "Golden Bear University",
                   "555-123-9876", "priya@example.edu"):
        assert secret not in out
    assert "social security" in out  # the actual question survives


def test_public_context_carries_no_identifying_facts():
    context = engine.public_context(PROFILE, [{"ruleId": "FICA_EXEMPT_F1"}])
    for secret in ("Priya", "Sharma", "Golden Bear", "University Dining"):
        assert secret not in context
    assert "F-1" in context and "FICA_EXEMPT_F1" in context


def test_channels_follow_consent():
    assert engine.channels_for({"smsConsent": False}) == ["chat"]
    assert engine.channels_for({"smsConsent": True}) == ["chat"]          # no number, no text
    assert engine.channels_for({"smsConsent": True, "phone": "+14155550123"}) == ["chat", "sms"]


# ---------- the supporting-run matcher ----------

@pytest.mark.parametrize("answer,page,found", [
    (ANSWER, IRS_PAGE, True),
    (ANSWER, UNRELATED_PAGE, False),
    ("short", IRS_PAGE, False),          # too short to be evidence of anything
    (ANSWER, "", False),                 # empty page
])
def test_supports(answer, page, found):
    from rules.download_sources import page_text
    assert bool(athena.supports(answer, page_text(page) if page else "")) is found
