"""Docket phoning the student, and the queue that decides when it should.

A call to a person is the most intrusive thing Docket does, so it is the most gated:

  * the student must have given a phone number and turned voice on (profiles.voiceConsent).
    No consent, no call, and the skip is logged with the reason.
  * the call must carry something that actually needs her: a finding, a document to approve, a
    group invitation, a refund that landed. Those arrive as queued notifications on the "voice"
    channel; this module never invents a reason to ring.
  * the one-sentence reason the agent opens with was written and checked by agents/guard.py, so the
    voice model is reading a sentence that has already passed the privacy checks rather than
    composing one from the student file.

Everything else the call needs it fetches live through the webhook tools in convex/http.ts, so a
call placed now cannot read out a fact that changed since it was queued.
"""
from __future__ import annotations

import os

from agents.guard import for_voice
from agents.store import log, mutation, query
from agents.voice.calls import CallError, normalise, place

AGENT = "voice"
AGENT_ENV = "CARTESIA_STUDENT_AGENT_ID"
PURPOSES = {"finding", "document_ready", "group_invite", "case_update", "refund", "research"}


def missing_settings() -> list[str]:
    return [k for k in ("CARTESIA_API_KEY", AGENT_ENV, "CARTESIA_FROM_NUMBER_ID") if not os.environ.get(k)]


def reachable(profile: dict) -> tuple[bool, str]:
    """Whether Docket may ring this student, and why not when it may not."""
    if not profile.get("phone"):
        return False, "no phone number on file"
    if not profile.get("voiceConsent"):
        return False, "the student has not turned on phone calls"
    if not normalise(profile["phone"]).startswith("+"):
        return False, f"phone number {profile['phone']!r} is not E.164"
    return True, ""


def call_student(profile: dict, purpose: str, headline: str, *, notification_id: str | None = None,
                 session=None) -> str | None:
    """Ring the student about one thing. Returns Cartesia's call id, or None if the call was skipped
    (always for a logged reason). `headline` is the already-checked sentence the agent opens with."""
    ok, why = reachable(profile)
    if not ok:
        log(AGENT, "student_call_skipped", f"Did not call about {purpose}: {why}", inputIds=[profile["_id"]])
        return None
    missing = missing_settings()
    if missing:
        log(AGENT, "student_call_skipped",
            f"Did not call about {purpose}: Cartesia not configured ({', '.join(missing)})",
            inputIds=[profile["_id"]])
        return None
    variables = {
        "profile_id": profile["_id"],
        "student_name": profile["name"].split()[0],
        "purpose": purpose,
        "headline": for_voice(headline),
        "notification_id": notification_id or "",
    }
    kwargs = {"agent_env": AGENT_ENV}
    if session is not None:
        kwargs["session"] = session
    try:
        call_id, dialled = place(profile["phone"], variables, **kwargs)
    except CallError as e:
        log(AGENT, "student_call_failed", f"Could not call about {purpose}: {e}", inputIds=[profile["_id"]])
        return None
    mutation("calls:logStudentCall", {
        "profileId": profile["_id"],
        "direction": "outbound",
        "purpose": purpose,
        "summary": for_voice(headline),
        "answeredBy": "The student",
        "toNumber": dialled,
        "callRequestId": call_id,
    })
    return call_id


def deliver_pending(limit: int = 5) -> int:
    """Place a call for every notification queued on the voice channel. Returns how many rang."""
    placed = 0
    for note in query("notifications:pending", {"channel": "voice", "limit": limit}):
        profile = query("profiles:get", {"profileId": note["profileId"]})
        if profile is None:
            mutation("notifications:markSent", {"notificationId": note["_id"], "error": "no such student"})
            continue
        call_id = call_student(profile, note["kind"], note["body"], notification_id=note["_id"])
        if call_id is None:
            # The reason is already in the activity log. Fall the message back to chat rather than
            # dropping it, so the student still hears about it.
            mutation("notifications:markSent", {"notificationId": note["_id"], "error": "could not place the call"})
            mutation("notifications:queue", {
                "profileId": note["profileId"], "channel": "chat", "kind": note["kind"],
                "title": note["title"], "body": note["body"],
                "refs": note.get("refs") or [], "awaiting": note.get("awaiting") or "none",
            })
            continue
        mutation("notifications:markSent", {"notificationId": note["_id"]})
        placed += 1
    return placed
