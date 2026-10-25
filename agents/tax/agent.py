"""Tax and status agent: runs the rules for a student and writes flags to Convex.

Runs when the Coordinator asks (Priya said "check my pay"), and on its own when the Ledger reports new
paystubs; then it tells the Coordinator what it found.

    .venv/bin/python -m agents.tax.agent
"""

import asyncio
import json
import os

from pathlib import Path

from uagents import Agent, Context

from agents.agentverse import add_mailbox_check
from agents.chat import add_chat, no_student, student
from agents.messages import (
    PORTS,
    Claim,
    Objection,
    Rebuttal,
    Verdict,
    FindingsReady, LocalFirstResolver, NewPaystub, RulesResult, RunRules, address_of,
)
from agents.messaging import ask, heard, tell
from agents.store import log, query
from agents.tax import advocate
from agents.tax import engine

agent = Agent(name="docket-tax", seed=os.environ["TAX_SEED"], port=PORTS["TAX"], mailbox=True,
              resolve=LocalFirstResolver(),
              description="Applies F-1 FICA, 20-hour and Form 8843 rules in code and argues the student's side in Docket's Hearing.",
              readme_path=str(Path(__file__).with_name("AGENTVERSE.md")),
              publish_agent_details=True)
add_mailbox_check(agent, "tax", PORTS["TAX"])


def build_claims(profile_id: str, written: list[dict]) -> tuple[dict | None, list[dict]]:
    """The claims Tax will argue: one per finding it wrote, plus the FICA claim even when the rule did not
    fire (any F-1 student with Social Security or Medicare withheld), which the Auditor may defeat."""
    profile = query("profiles:get", {"profileId": profile_id})
    if profile is None:
        return None, []
    stubs = query("paystubs:listByProfile", {"profileId": profile_id})
    by_rule = {w["id"]: w for w in written}
    fica = by_rule.get(advocate.FICA)
    source = query("sources:getByUrl", {"url": advocate.rule(advocate.FICA)["source_url"]})
    claims = []
    claim = advocate.fica_claim(profile, stubs, {"_id": fica["flagId"]} if fica else None,
                                fica["hit"] if fica else None, source)
    if claim:
        claims.append(claim)
    hours = by_rule.get(advocate.HOURS)
    if hours:
        claims.append(advocate.hours_claim({"_id": hours["flagId"], "quote": hours["quote"], "sourceId": hours["sourceId"]},
                                           hours["hit"], engine.paystub_ids(hours["hit"], stubs)))
    for c in claims:
        c["opening"] = advocate.opening(c, profile)
    return profile, claims


async def hold_hearings(ctx: Context, profile_id: str, written: list[dict]) -> list[dict]:
    """Argue each claim with the Auditor: Claim -> Objection -> Rebuttal -> Verdict. Returns the verdicts."""
    profile, claims = await asyncio.to_thread(build_claims, profile_id, written)
    results = []
    for claim in claims:
        rid, fid = claim["rule_id"], claim["flag_id"]
        objection, _ = await ask(ctx, "tax", "AUDITOR", Claim(profile_id=profile_id, rule_id=rid, flag_id=fid,
                                 claim_json=json.dumps(claim)), Objection, f"claim {rid}: {claim['opening'][:120]}")
        if objection is None:
            await asyncio.to_thread(log, "tax", "hearing_failed", f"{rid}: the Auditor did not answer the claim")
            continue
        objs = json.loads(objection.objections_json)
        rebuttals = [advocate.rebut(o, claim, profile) for o in objs]
        summary = ", ".join(f"{r['objection_id']} {r['outcome']}" for r in rebuttals) or "no objections"
        verdict, _ = await ask(ctx, "tax", "AUDITOR", Rebuttal(
            profile_id=profile_id, rule_id=rid, flag_id=fid, claim_json=json.dumps(claim),
            objections_json=objection.objections_json, rebuttals_json=json.dumps(rebuttals)), Verdict, summary)
        if verdict is None:
            await asyncio.to_thread(log, "tax", "hearing_failed", f"{rid}: no verdict from the Auditor")
            continue
        results.append({"rule_id": rid, "flag_id": fid, "hearing_id": verdict.hearing_id, "verdict": verdict.verdict,
                        "reason": verdict.reason})
    return results


@agent.on_interval(period=float(os.environ.get("TAX_HEARING_POLL_SECONDS", "4")))
async def hearing_on_request(ctx: Context):
    """Hold the hearing again when the Hearing game asks for one.

    The game runs in a browser and cannot send a uAgent message, so it leaves a request in Convex
    and this picks it up. Without it the game replayed the hearing the agents held earlier: the
    same words on screen, but nothing actually running while you watch, and the Agentverse
    interaction counts never moved. Now watching the game and watching the agents argue are the
    same thing.
    """
    try:
        ask_row = await asyncio.to_thread(query, "game:hearingRequested")
    except Exception:  # noqa: BLE001 - a Convex blip must not kill the interval
        return
    if not ask_row or not ask_row.get("requested") or not ask_row.get("profileId"):
        return
    pid = ask_row["profileId"]
    await asyncio.to_thread(log, "tax", "hearing_rerun",
                            "The Hearing game asked for this hearing live; arguing it again")
    try:
        flags = await asyncio.to_thread(engine.run, pid)
        await hold_hearings(ctx, pid, flags)
    except Exception:
        ctx.logger.exception("the requested hearing failed")


@agent.on_message(RunRules, replies=RulesResult)
async def run_rules(ctx: Context, sender: str, msg: RunRules):
    try:
        flags = await asyncio.to_thread(engine.run, msg.profile_id)
        hearings = await hold_hearings(ctx, msg.profile_id, flags)
        await ctx.send(sender, RulesResult(flags_json=json.dumps(flags), hearings_json=json.dumps(hearings)))
    except Exception as e:
        ctx.logger.exception("rules run failed")
        await ctx.send(sender, RulesResult(flags_json="[]", error=str(e)))


@agent.on_message(NewPaystub)
async def on_new_paystubs(ctx: Context, sender: str, msg: NewPaystub):
    if sender != address_of("LEDGER"):
        return
    await heard("tax", sender, msg, f"{msg.count} new paystubs to check")
    try:
        flags = await asyncio.to_thread(engine.run, msg.profile_id)
        await hold_hearings(ctx, msg.profile_id, flags)
    except Exception:
        ctx.logger.exception("rules run on new paystubs failed")
        return
    await tell(ctx, "tax", "COORDINATOR", FindingsReady(
        profile_id=msg.profile_id, paystub_count=msg.count, flags_json=json.dumps(flags)),
        f"{len(flags)} findings on {msg.count} new paystubs")


# --- ASI:One ------------------------------------------------------------------
# Which rules fired, and the clause each one stands on. Rules run in code; nothing here is recalled.
def answer(question: str) -> str:
    from agents.store import dollars, query
    p = student()
    if p is None:
        return no_student()
    flags = query("flags:listByProfile", {"profileId": p["_id"]})
    if not flags:
        return ("I've run the rules and nothing fired for this student. No finding means no case: "
                "I don't raise anything I can't quote a source for.")
    lines = []
    for f in flags:
        amount = f" - {dollars(f['amountCents'])}" if f.get("amountCents") else ""
        lines.append(f"- **{f['ruleId']}**{amount} ({f.get('status', 'open')})")
        quote = (f.get("quote") or "").strip()
        if quote:
            lines.append(f"  > {quote[:240]}")
    return (
        "I'm Docket's Tax and status agent. I run the F-1 rules against the student's own file, in "
        "code, and a finding only ships if I can quote the official clause word for word.\n\n"
        + "\n".join(lines) +
        "\n\nEach quote is checked against the stored copy of the source page before it is shown. "
        "If a page changes and the sentence is no longer on it, I hold that rule's findings back."
    )


add_chat(agent, "tax", answer)


if __name__ == "__main__":
    agent.run()
