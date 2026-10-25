"""Auditor agent: argues the employer's side of each finding in the Hearing, and issues the verdict in code.

    .venv/bin/python -m agents.auditor.agent

Tax (the Advocate) sends a Claim; the Auditor answers with every Objection it can raise from the student
file; Tax answers each with a Rebuttal; the Auditor decides the Verdict, stores the whole Hearing in
Convex (hearings), and sends the Verdict to Tax and to the Caseworker.
"""

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from uagents import Agent, Context

from agents.agentverse import add_mailbox_check
from agents.auditor.objections import argument, objections
from agents.auditor.verdict import decide
from agents.messages import PORTS, Claim, LocalFirstResolver, Objection, Rebuttal, Verdict, address_of
from agents.messaging import heard, tell
from agents.store import log, mutation, query

load_dotenv()

agent = Agent(name="docket-auditor", seed=os.environ["AUDITOR_SEED"], port=PORTS["AUDITOR"], mailbox=True,
              resolve=LocalFirstResolver(),
              description="Argues the employer's side of every F-1 tax finding in Docket's Hearing; the verdict is decided in code.",
              readme_path=str(Path(__file__).with_name("AGENTVERSE.md")),
              publish_agent_details=True)
add_mailbox_check(agent, "auditor", PORTS["AUDITOR"])


def rounds(claim: dict, objs: list[dict], rebuttals: list[dict]) -> list[dict]:
    """The Hearing as stored: the Advocate's claim, then each objection and its answer, in order."""
    now = datetime.now(timezone.utc).isoformat()
    answers = {r["objection_id"]: r for r in rebuttals}
    claim_evidence = [x for x in [*claim.get("paystub_ids", []), claim.get("source_id")] if x]
    out = [{"round": 1, "side": "advocate", "argument": claim["opening"], "evidenceIds": claim_evidence, "at": now}]
    for o in objs:
        out.append({"round": len(out) + 1, "side": "auditor", "objectionId": o["id"], "argument": argument(o),
                    "evidenceIds": [str(e) for e in o["evidence_ids"]], "at": now})
        a = answers.get(o["id"])
        if a:
            out.append({"round": len(out) + 1, "side": "advocate", "objectionId": o["id"],
                        "argument": f"{a['argument']} [{a['outcome']}]",
                        "evidenceIds": [str(e) for e in a["evidence_ids"]], "at": now})
    return out


@agent.on_message(Claim)
async def on_claim(ctx: Context, sender: str, msg: Claim):
    if sender != address_of("TAX"):
        return
    await heard("auditor", sender, msg, f"claim {msg.rule_id}")
    claim = json.loads(msg.claim_json)
    profile = await asyncio.to_thread(query, "profiles:get", {"profileId": msg.profile_id}) or {}
    objs = objections(claim, profile)
    await tell(ctx, "auditor", "TAX", Objection(profile_id=msg.profile_id, rule_id=msg.rule_id,
               objections_json=json.dumps(objs)), f"{len(objs)} objections: {', '.join(o['id'] for o in objs)}")


@agent.on_message(Rebuttal)
async def on_rebuttal(ctx: Context, sender: str, msg: Rebuttal):
    if sender != address_of("TAX"):
        return
    await heard("auditor", sender, msg, f"rebuttals for {msg.rule_id}")
    claim, objs, rebuttals = json.loads(msg.claim_json), json.loads(msg.objections_json), json.loads(msg.rebuttals_json)
    result = decide(claim, objs, rebuttals)
    record = {"profileId": msg.profile_id, "ruleId": msg.rule_id, "rounds": rounds(claim, objs, rebuttals),
              "verdict": result["verdict"], "reason": result["reason"]}
    if msg.flag_id:
        record["flagId"] = msg.flag_id
    try:
        hearing_id = await asyncio.to_thread(mutation, "hearings:record", record)
    except Exception as e:
        ctx.logger.exception("storing the hearing failed")
        await asyncio.to_thread(log, "auditor", "hearing_store_failed", str(e)[:200])
        hearing_id = ""
    verdict = Verdict(profile_id=msg.profile_id, rule_id=msg.rule_id, flag_id=msg.flag_id, hearing_id=hearing_id,
                      verdict=result["verdict"], reason=result["reason"], amount_cents=claim.get("amount_cents", 0))
    await tell(ctx, "auditor", "TAX", verdict, f"{msg.rule_id}: {result['verdict']}")
    await tell(ctx, "auditor", "CASEWORKER", verdict, f"{msg.rule_id}: {result['verdict']}")


if __name__ == "__main__":
    agent.run()
