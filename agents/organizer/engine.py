"""Finding the pattern, asking each student, and acting for the ones who said yes."""
from __future__ import annotations

from agents import guard
from agents.researcher import athena, engine as research
from agents.store import dollars, log, mutation, query

AGENT = "organizer"
GROUP_RULES = ("FICA_EXEMPT_F1",)  # the findings worth asking together about
MIN_TO_ACT = 2  # joined members before Docket sends the combined request


# ---------------------------------------------------------------------------
# 1. Find the pattern and invite everyone in it
# ---------------------------------------------------------------------------

def find_and_invite() -> int:
    """Form a group for every employer-and-rule pattern on file and invite the students in it.
    Returns how many students were newly invited."""
    invited_total = 0
    for rule_id in GROUP_RULES:
        for row in query("groups:candidates", {"ruleId": rule_id}):
            result = mutation("groups:formFromPattern", {
                "employer": row["employer"],
                "ruleId": rule_id,
                "summary": summary_for(row["employer"], rule_id, row["flagged"], row["totalCents"]),
                "members": [{"profileId": m["profileId"], "flagId": m["flagId"],
                             "amountCents": m["amountCents"]} for m in row["members"]],
            })
            for profile_id in result["invited"]:
                invite(profile_id, result["groupId"], row["employer"], row["flagged"])
                invited_total += 1
    return invited_total


def summary_for(employer: str, rule_id: str, flagged: int, total_cents: int) -> str:
    what = ("Social Security and Medicare tax withheld from students who are likely exempt"
            if rule_id == "FICA_EXEMPT_F1" else rule_id)
    return (f"{flagged} students at {employer} have the same finding: {what}. "
            f"{dollars(total_cents)} withheld in total across all of them.")


def invite(profile_id: str, group_id: str, employer: str, affected: int) -> None:
    """Ask one student whether she wants to join. Her standing preference can answer for her."""
    profile = query("profiles:get", {"profileId": profile_id})
    if profile is None or profile.get("simulated"):
        return  # the simulated cohort exists to make the pattern real; it is never messaged
    preference = profile.get("groupPreference") or "ask"
    if preference == "never":
        mutation("groups:respond", {"groupId": group_id, "profileId": profile_id, "join": False,
                                    "via": "standing preference"})
        return
    if preference == "always":
        mutation("groups:respond", {"groupId": group_id, "profileId": profile_id, "join": True,
                                    "via": "standing preference"})
        return

    facts = {"group_employer": employer, "group_invited": affected}
    fallback = (f"{affected} students at {employer} have the same problem with their paychecks as you. "
                f"They're asking payroll to fix it together, which is harder to ignore than one request. "
                f"Do you want to join? Your own case keeps going either way, and joining costs you nothing.")
    rendered = guard.speak(
        purpose=("Invite the student to join a group request to her employer's payroll. Say how many "
                 "students are affected, that joining does not change or pause her own case, and that "
                 "she can say no. Do not name any other student."),
        facts=facts, channel="chat", audience="group", fallback=fallback, log_fn=log, agent=AGENT)

    body = rendered.text
    for channel in research.channels_for(profile):
        mutation("notifications:queue", {
            "profileId": profile_id, "channel": channel, "kind": "group_invite",
            "title": f"Join the group request to {employer}?",
            "body": guard.for_sms(body) if channel == "sms" else body,
            "refs": [group_id], "awaiting": "group_optin",
        })
    log(AGENT, "group_invited", f"Asked a student whether to join the {employer} group case",
        inputIds=[profile_id, group_id])


# ---------------------------------------------------------------------------
# 2. Act for the students who joined
# ---------------------------------------------------------------------------

def act_on_open_groups() -> int:
    """For every group with enough joined members, prepare the combined request. Returns how many."""
    acted = 0
    for hydrated in query("groups:list"):
        if hydrated["state"] != "open" or hydrated["joinedCount"] < MIN_TO_ACT:
            continue
        joined = [m for m in hydrated["members"] if m["state"] == "joined"]
        mutation("groups:setState", {
            "groupId": hydrated["_id"], "state": "contacting",
            "note": (f"{len(joined)} students joined the {hydrated['employer']} group case; "
                     f"combined request for {dollars(hydrated['joinedCents'])} prepared"),
        })
        # The document is filled in by the Filer, which only ever reads joined members.
        for member in joined:
            mutation("documents:draft", draft_for(hydrated, member, joined))
        acted += 1
    return acted


def draft_for(group: dict, member: dict, joined: list[dict]) -> dict:
    """Each joined student gets her own copy of the group request to approve. The letter states the
    group's size and total, and her own amount; it never lists the other students."""
    employer = group["employer"]
    body = (
        f"To {employer} Payroll\n"
        f"Re: Social Security and Medicare withheld from nonresident F-1 students\n\n"
        f"{len(joined)} students employed by {employer} have found the same problem on their "
        f"paychecks: Social Security and Medicare tax was withheld from pay that nonresident alien "
        f"students in F-1 status are generally exempt from. Together they are asking for "
        f"{dollars(group['joinedCents'])}.\n\n"
        f"This copy is sent by {member['name']}, with her permission, by Docket, an AI assistant. "
        f"Her own share is {dollars(member['amountCents'])}.\n\n"
        f"Because the same error affects {len(joined)} people on the same payroll, this is likely a "
        f"payroll configuration problem rather than {len(joined)} separate mistakes. Please:\n"
        f"1. Review the F-1 exemption settings for all nonresident student employees;\n"
        f"2. Refund the amounts withheld in error; and\n"
        f"3. Stop withholding these taxes from future paychecks.\n\n"
        f"If you cannot refund them, please say so in writing, so each student can claim it from the "
        f"IRS with Form 843 and Form 8316."
    )
    return {
        "profileId": member["profileId"],
        "kind": "group_request",
        "title": f"Group refund request to {employer}",
        "fields": [
            {"label": "Employer", "value": employer, "source": "paystubs.employer"},
            {"label": "Students joined", "value": str(len(joined)), "source": "groupMembers (joined only)"},
            {"label": "Combined amount", "value": dollars(group["joinedCents"]), "source": "sum of joined members' flags"},
            {"label": "Your share", "value": dollars(member["amountCents"]), "source": "flags.amountCents"},
        ],
        "body": body,
        "submitTo": f"{employer} payroll",
        "groupId": group["_id"],
    }


# ---------------------------------------------------------------------------
# 3. Who else is worth contacting about a pattern this size
# ---------------------------------------------------------------------------

def research_contacts(group: dict) -> int:
    """Ask the research agent who handles this kind of case, and record what it finds as contacts.

    Nothing here is dialled: a contact found by research is stored unverified, shown to the student,
    and still only ever reached through agents/voice/calls.py, which redirects every call to the
    demo number. Finding a number and calling it are deliberately separate steps.
    """
    question = (
        "For a group of international students whose university employer withheld Social Security "
        "and Medicare tax from them in error, which US organisations help with this: the IRS "
        "taxpayer advocate, university international student offices, and free or low-cost legal "
        "aid clinics for immigrants? Give the official name, the public phone number and the page "
        "it is published on for each.")
    finding = athena.research(question, "Context (no identifying details): visa: F-1; country: United States")
    if not finding.ok:
        log(AGENT, "contact_research_failed", finding.error[:200], inputIds=[group["_id"]])
        return 0
    stored = research.store(None, "ask", f"Who to contact about the {group['employer']} pattern",
                            finding, question=question, actionable=False)
    mutation("groups:setState", {
        "groupId": group["_id"], "state": group["state"],
        "note": f"Researched who else handles cases like this ({len(finding.sources)} sources)",
    })
    log(AGENT, "contact_research_done", f"Stored research {stored} for the {group['employer']} group",
        inputIds=[group["_id"]], outputIds=[stored])
    return len([s for s in finding.sources if s.verified])
