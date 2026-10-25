"""Group cases: who is counted, who is told what, and who is never messaged.

The invariant under test throughout: an invited student is not a member. Her amount is not in the
total and her name is not in the letter until she has said yes.
"""
import pytest

from agents import guard
from agents.organizer import engine

EMPLOYER = "University Dining Services"

GROUP = {
    "_id": "g1", "employer": EMPLOYER, "ruleId": "FICA_EXEMPT_F1", "state": "open",
    "joinedCount": 3, "joinedCents": 96740,
    "members": [
        {"profileId": "p1", "name": "Priya Sharma", "amountCents": 44064, "state": "joined"},
        {"profileId": "p2", "name": "Simulated student 1", "amountCents": 30000, "state": "joined"},
        {"profileId": "p3", "name": "Simulated student 2", "amountCents": 22676, "state": "joined"},
        {"profileId": "p4", "name": "Simulated student 3", "amountCents": 50000, "state": "invited"},
        {"profileId": "p5", "name": "Simulated student 4", "amountCents": 11111, "state": "declined"},
    ],
}


class Recorder:
    """Stands in for Convex: records mutations, answers queries from a fixture."""
    def __init__(self, data=None):
        self.data, self.mutations = data or {}, []

    def mutation(self, name, args=None):
        self.mutations.append((name, args or {}))
        return {"groupId": "g1", "invited": ["p1"]} if name == "groups:formFromPattern" else None

    def query(self, name, args=None):
        return self.data.get(name, [])


@pytest.fixture
def convex(monkeypatch):
    r = Recorder()
    monkeypatch.setattr(engine, "mutation", r.mutation)
    monkeypatch.setattr(engine, "query", r.query)
    monkeypatch.setattr(engine, "log", lambda *a, **k: None)
    return r


# ---------- the combined letter ----------

def test_the_letter_counts_only_joined_members(convex):
    joined = [m for m in GROUP["members"] if m["state"] == "joined"]
    draft = engine.draft_for(GROUP, joined[0], joined)
    body = draft["body"]
    assert "3 students" in body          # not 5, and not 4
    assert "$967.40" in body             # joinedCents, which excludes the invited and declined
    assert "$500.00" not in body         # the invited student's amount is nowhere in it


def test_the_letter_names_only_the_student_sending_it(convex):
    joined = [m for m in GROUP["members"] if m["state"] == "joined"]
    body = engine.draft_for(GROUP, joined[0], joined)["body"]
    assert "Priya Sharma" in body
    for other in ("Simulated student 1", "Simulated student 2", "Simulated student 3"):
        assert other not in body


def test_each_member_gets_her_own_copy_with_her_own_share(convex):
    joined = [m for m in GROUP["members"] if m["state"] == "joined"]
    for member in joined:
        draft = engine.draft_for(GROUP, member, joined)
        fields = {f["label"]: f["value"] for f in draft["fields"]}
        assert draft["profileId"] == member["profileId"]
        assert fields["Your share"] == engine.dollars(member["amountCents"])
        assert fields["Combined amount"] == "$967.40"
        assert fields["Students joined"] == "3"


# ---------- who gets asked ----------

def test_a_simulated_student_is_never_messaged(convex):
    """The simulated cohort exists so the pattern is real. Messaging one would be messaging nobody."""
    convex.data["profiles:get"] = {"_id": "p2", "name": "Simulated student 1", "simulated": True}
    engine.invite("p2", "g1", EMPLOYER, 4)
    assert convex.mutations == []


def test_a_standing_never_answers_without_asking(convex, monkeypatch):
    convex.data["profiles:get"] = {"_id": "p1", "name": "Priya Sharma", "groupPreference": "never"}
    engine.invite("p1", "g1", EMPLOYER, 4)
    names = [name for name, _ in convex.mutations]
    assert names == ["groups:respond"]
    assert convex.mutations[0][1]["join"] is False
    assert "notifications:queue" not in names  # she asked not to be asked


def test_a_standing_always_joins_without_asking(convex):
    convex.data["profiles:get"] = {"_id": "p1", "name": "Priya Sharma", "groupPreference": "always"}
    engine.invite("p1", "g1", EMPLOYER, 4)
    assert convex.mutations[0][0] == "groups:respond"
    assert convex.mutations[0][1]["join"] is True


def test_the_default_is_to_ask_her(convex, monkeypatch):
    monkeypatch.setattr(guard, "write", lambda *a, **k: "Four students have the same problem. Join?")
    convex.data["profiles:get"] = {"_id": "p1", "name": "Priya Sharma"}
    engine.invite("p1", "g1", EMPLOYER, 4)
    queued = [args for name, args in convex.mutations if name == "notifications:queue"]
    assert queued and queued[0]["awaiting"] == "group_optin"
    assert queued[0]["kind"] == "group_invite"


def test_the_invitation_cannot_carry_another_student(convex, monkeypatch):
    """The group audience has no key that could hold a name or an amount, so even a writer that
    tried could not put one in."""
    seen = {}

    def fake_write(purpose, facts, channel, audience, excerpts=None):
        seen.update(facts)
        return "Four students at University Dining Services have the same problem. Join them?"

    monkeypatch.setattr(guard, "write", fake_write)
    convex.data["profiles:get"] = {"_id": "p1", "name": "Priya Sharma"}
    engine.invite("p1", "g1", EMPLOYER, 4)
    assert set(seen) <= {"group_employer", "group_invited"}
    assert "Priya" not in str(seen)


def test_the_fallback_invitation_is_safe_too(convex, monkeypatch):
    """When the writing layer is down the student still gets asked, with code-written words."""
    monkeypatch.setattr(guard, "write", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("down")))
    convex.data["profiles:get"] = {"_id": "p1", "name": "Priya Sharma"}
    engine.invite("p1", "g1", EMPLOYER, 4)
    queued = [args for name, args in convex.mutations if name == "notifications:queue"]
    assert queued
    body = queued[0]["body"]
    assert "4 students" in body and EMPLOYER in body
    assert "Priya" not in body


# ---------- acting on the group ----------

def test_a_group_below_the_threshold_is_not_acted_on(convex):
    convex.data["groups:list"] = [{**GROUP, "joinedCount": 1}]
    assert engine.act_on_open_groups() == 0
    assert convex.mutations == []


def test_a_group_that_is_not_open_is_not_acted_on(convex):
    convex.data["groups:list"] = [{**GROUP, "state": "closed"}]
    assert engine.act_on_open_groups() == 0


def test_an_open_group_drafts_one_document_per_joined_member(convex):
    convex.data["groups:list"] = [GROUP]
    assert engine.act_on_open_groups() == 1
    drafts = [args for name, args in convex.mutations if name == "documents:draft"]
    assert len(drafts) == 3                                   # joined only
    assert {d["profileId"] for d in drafts} == {"p1", "p2", "p3"}
    assert all(d["groupId"] == "g1" for d in drafts)


def test_the_summary_states_the_pattern_plainly():
    summary = engine.summary_for(EMPLOYER, "FICA_EXEMPT_F1", 4, 140804)
    assert "4 students" in summary and EMPLOYER in summary and "$1,408.04" in summary
