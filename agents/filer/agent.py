"""Filer agent: fills the student's forms in, shows her, and submits only what she approved.

    .venv/bin/python -m agents.filer.agent
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from uagents import Agent, Context

from agents.agentverse import add_mailbox_check
from agents.chat import add_chat, no_student, student
from agents.filer import engine
from agents.messages import PORTS, DocumentReady, FillDocument, LocalFirstResolver, address_of
from agents.messaging import heard, tell
from agents.store import log, query

load_dotenv()

agent = Agent(name="docket-filer", seed=os.environ["FILER_SEED"], port=PORTS["FILER"], mailbox=True,
              resolve=LocalFirstResolver(),
              description="Fills in an F-1 student's tax forms from her stored records, shows her the "
                          "filled form, and submits only what she approves.",
              readme_path=str(Path(__file__).with_name("AGENTVERSE.md")),
              publish_agent_details=True)
add_mailbox_check(agent, "filer", PORTS["FILER"])

POLL_SECONDS = float(os.environ.get("FILER_POLL_SECONDS", "30"))


@agent.on_message(FillDocument, replies=DocumentReady)
async def on_fill(ctx: Context, sender: str, msg: FillDocument):
    await heard("filer", sender, msg, f"fill {msg.kind}", inputIds=[msg.profile_id])
    try:
        document_id = await asyncio.to_thread(engine.fill, msg.profile_id, msg.kind,
                                              msg.flag_id, msg.group_id)
        if document_id is None:
            return  # the reason is already logged; a form with a missing fact is not filled in
        document = await asyncio.to_thread(query, "documents:get", {"documentId": document_id})
        await tell(ctx, "filer", "COORDINATOR", DocumentReady(
            profile_id=msg.profile_id, document_id=document_id, kind=msg.kind,
            title=document["title"], submit_to=document["submitTo"]),
            f"{document['title']} waiting for approval", inputIds=[document_id])
    except Exception:
        ctx.logger.exception("filling the document failed")


@agent.on_interval(period=POLL_SECONDS)
async def sweep(ctx: Context):
    """Fill in anything now due, and send anything she has approved since the last pass."""
    try:
        profile = next((p for p in await asyncio.to_thread(query, "profiles:list")
                        if not p.get("simulated")), None)
        if profile is not None:
            made = await asyncio.to_thread(engine.fill_what_is_due, profile["_id"])
            if made:
                ctx.logger.info(f"filled in {len(made)} form(s) for review")
        sent = await asyncio.to_thread(engine.submit_approved)
        if sent:
            ctx.logger.info(f"submitted {sent} approved document(s)")
    except Exception:
        ctx.logger.exception("the filer sweep failed")


# --- ASI:One ------------------------------------------------------------------
# Forms filled from stored records. Every field names the record it came from; none are model-written.
def answer(question: str) -> str:
    from agents.store import query
    p = student()
    docs = query("documents:forProfile", {"profileId": p["_id"]}) if p else []
    out = ["I'm Docket's Filer. I fill the student's forms in from records already in her file - "
           "Form 8843, the refund request, and Forms 843 and 8316 for the IRS route - and I submit "
           "only what she has approved.\n"]
    if not docs:
        out.append("Nothing is filled in yet for this student.")
    else:
        for d in docs:
            out.append(f"- **{d.get('kind', 'a form')}** - {d.get('state', 'draft').replace('_', ' ')}"
                       f" ({len(d.get('fields') or [])} fields)")
    out.append("\nEvery field shows which record it came from, so nothing on a tax form was written "
               "by a model. A fact I don't have stops the form rather than being filled with a "
               "plausible guess. **Docket cannot file with the IRS** and says so plainly.")
    return "\n".join(out)


add_chat(agent, "filer", answer)


if __name__ == "__main__":
    agent.run()
