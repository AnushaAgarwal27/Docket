import { httpRouter } from "convex/server";
import { env, httpAction } from "./_generated/server";
import { api, internal } from "./_generated/api";

// Webhook tools for Docket's two Cartesia voice agents (see docs/CARTESIA.md).
//
// The payroll caller:
//   POST /cartesia/case-summary   body {case_id}                      -> plain-text facts for the call
//   POST /cartesia/call-outcome   body {case_id, result, answered_by,  -> runs cases.logCallOutcome
//                                       summary, promised_by?, reference_number?}
//   result is one of promised, stalled, refused, needs_student
//
// The student line (both directions):
//   POST /cartesia/identify       body {from_number}                  -> who is calling, by their number
//   POST /cartesia/student-brief  body {profile_id}                   -> what is open on their file
//   POST /cartesia/ask            body {profile_id, question}         -> answer now, or take the question
//   POST /cartesia/decision       body {profile_id, subject, answer}  -> a yes or no said out loud
//   POST /cartesia/student-call   body {profile_id, summary, ...}     -> log the call when it ends
//
// Every route requires "Authorization: Bearer <CARTESIA_TOOL_TOKEN>". Responses are short plain text
// because Cartesia hands the body to the voice model as the tool result.
//
// What these routes will not do: look a student up by anything but the number that rang or the
// profile id we placed the call with, return more than one student, or expose a bank row. A tool
// that cannot identify one student answers with a sentence saying so and nothing else.

const http = httpRouter();
const RESULTS = ["promised", "stalled", "refused", "needs_student"] as const;
type Result = (typeof RESULTS)[number];

const text = (body: string, status = 200) =>
  new Response(body, { status, headers: { "Content-Type": "text/plain; charset=utf-8" } });

function authorized(req: Request): boolean {
  const token = env.CARTESIA_TOOL_TOKEN;
  return typeof token === "string" && token.length > 0 && req.headers.get("Authorization") === `Bearer ${token}`;
}

async function readObject(req: Request): Promise<Record<string, unknown> | null> {
  try {
    const body: unknown = await req.json();
    return body !== null && typeof body === "object" && !Array.isArray(body) ? (body as Record<string, unknown>) : null;
  } catch {
    return null;
  }
}

/** First non-empty string among the given keys (Cartesia sends snake_case; accept camelCase too). */
function field(body: Record<string, unknown>, ...keys: string[]): string | undefined {
  for (const k of keys) {
    const value = body[k];
    if (typeof value === "string" && value.trim() !== "") return value.trim();
    if (typeof value === "number") return String(value);
  }
  return undefined;
}

http.route({
  path: "/cartesia/case-summary",
  method: "POST",
  handler: httpAction(async (ctx, req) => {
    if (!authorized(req)) return text("Unauthorized.", 401);
    const body = await readObject(req);
    const caseId = body && field(body, "case_id", "caseId");
    if (!caseId) return text("Missing case_id.", 400);
    const summary = await ctx.runQuery(internal.cartesia.caseSummary, { caseId });
    if (summary === null) return text(`No case found for ${caseId}. Apologize, say you will call back, and end the call.`, 404);
    return text(summary.text);
  }),
});

http.route({
  path: "/cartesia/call-outcome",
  method: "POST",
  handler: httpAction(async (ctx, req) => {
    if (!authorized(req)) return text("Unauthorized.", 401);
    const body = await readObject(req);
    if (body === null) return text("Body must be a JSON object.", 400);
    const caseId = field(body, "case_id", "caseId");
    const result = field(body, "result");
    const answeredBy = field(body, "answered_by", "answeredBy") ?? "Payroll office";
    const summary = field(body, "summary");
    if (!caseId || !summary || !result || !(RESULTS as readonly string[]).includes(result)) {
      return text(`Need case_id, summary, and result (one of ${RESULTS.join(", ")}).`, 400);
    }
    const found = await ctx.runQuery(internal.cartesia.caseSummary, { caseId });
    if (found === null) return text(`No case found for ${caseId}.`, 404);
    const promisedBy = field(body, "promised_by", "promisedBy");
    const referenceNo = field(body, "reference_number", "referenceNo", "reference");
    try {
      await ctx.runMutation(api.cases.logCallOutcome, {
        caseId: found.caseId,
        answeredBy,
        summary,
        result: result as Result,
        ...(promisedBy ? { promisedBy } : {}),
        ...(referenceNo ? { referenceNo } : {}),
      });
    } catch (e) {
      const reason = e instanceof Error ? e.message.split("\n")[0] : "unknown error";
      // The voice agent is told to end the call politely, so payroll hears a normal goodbye and a
      // failure sounds exactly like a success. That is right for payroll and wrong for us: a
      // rejected write would otherwise be invisible until someone went looking in the database.
      // Leave a row saying what was lost and why.
      await ctx.runMutation(api.activity.log, {
        agent: "voice",
        action: "call_outcome_rejected",
        detail: `Payroll said "${result}" on case ${caseId} but it could not be recorded: ${reason}. ` +
          `The call ended normally, so nothing on the call itself showed this.`,
        inputIds: [caseId],
      });
      return text(`Could not record the outcome (${reason}). Thank them and end the call; the team will follow up.`, 409);
    }
    const next =
      result === "promised" ? `Recorded: refund promised${promisedBy ? ` by ${promisedBy}` : ""}${referenceNo ? `, reference ${referenceNo}` : ""}.`
      : result === "stalled" ? "Recorded: payroll has not committed to a date. A written request will follow."
      : result === "refused" ? "Recorded: payroll will not refund. A written request or an IRS claim will follow."
      : "Recorded: payroll needs the student on the line. A three-way call will be scheduled.";
    return text(`${next} Thank them and end the call.`);
  }),
});

// ---------------------------------------------------------------------------
// The student line
// ---------------------------------------------------------------------------

http.route({
  path: "/cartesia/identify",
  method: "POST",
  handler: httpAction(async (ctx, req) => {
    if (!authorized(req)) return text("Unauthorized.", 401);
    const body = await readObject(req);
    const from = body && field(body, "from_number", "fromNumber", "caller", "from");
    if (!from) return text("Missing from_number.", 400);
    const who = await ctx.runQuery(internal.voice.identify, { fromNumber: from });
    if (who === null) {
      return text(
        "I do not recognise this number, so I cannot discuss anyone's file. " +
        "Say that Docket can only talk about an account from the number on it, offer to help them add " +
        "this number from the Docket dashboard, and end the call politely.",
      );
    }
    return text(
      `This is ${who.name}. Greet her by her first name, ${who.firstName}. ` +
      `Her profile_id is ${who.profileId}; use it for every other tool on this call.`,
    );
  }),
});

http.route({
  path: "/cartesia/student-brief",
  method: "POST",
  handler: httpAction(async (ctx, req) => {
    if (!authorized(req)) return text("Unauthorized.", 401);
    const body = await readObject(req);
    const profileId = body && field(body, "profile_id", "profileId");
    if (!profileId) return text("Missing profile_id.", 400);
    const found = await ctx.runQuery(internal.voice.studentBrief, { profileId });
    if (found === null) return text("I could not find that file. Apologise and offer to call back.", 404);
    return text(found.text);
  }),
});

http.route({
  path: "/cartesia/ask",
  method: "POST",
  handler: httpAction(async (ctx, req) => {
    if (!authorized(req)) return text("Unauthorized.", 401);
    const body = await readObject(req);
    const profileId = body && field(body, "profile_id", "profileId");
    const question = body && field(body, "question", "q", "text");
    if (!profileId || !question) return text("Need profile_id and question.", 400);
    // Answer from what we already hold and have already checked. Anything else becomes a real
    // research job rather than a guess made up on the call.
    const stored = await ctx.runQuery(internal.voice.storedAnswer, { profileId, question });
    if (stored !== null) {
      const hedge = stored.confidence === "high" ? "" :
        " Say that this one is not certain and that she should confirm it with her international student office.";
      return text(`${stored.answer}${hedge}`);
    }
    const requestId = await ctx.runMutation(internal.voice.askResearch, {
      profileId, question, askedVia: "voice",
    });
    if (requestId === null) return text("I could not find that file. Apologise and offer to call back.", 404);
    return text(
      "You do not know the answer to this yet, and you must not guess. Tell her you are handing it to " +
      "Docket's research agent, that it will look through the official sources and the latest news, and " +
      "that she will get the answer as a message shortly. Then ask if there is anything else.",
    );
  }),
});

http.route({
  path: "/cartesia/decision",
  method: "POST",
  handler: httpAction(async (ctx, req) => {
    if (!authorized(req)) return text("Unauthorized.", 401);
    const body = await readObject(req);
    const profileId = body && field(body, "profile_id", "profileId");
    const subject = body && field(body, "subject", "about");
    const answer = body && field(body, "answer", "decision", "yes");
    if (!profileId || !subject || !answer) return text("Need profile_id, subject and answer.", 400);
    if (!["refund", "document", "group"].includes(subject)) {
      return text("subject must be one of refund, document, group.", 400);
    }
    const said = answer.trim().toLowerCase();
    const YES = ["yes", "y", "true", "approve", "approved", "join", "agree", "ok", "okay"];
    const NO = ["no", "n", "false", "decline", "declined", "reject", "skip", "not now"];
    if (!YES.includes(said) && !NO.includes(said)) {
      // A half-heard answer must never be read as consent.
      return text("I did not catch that clearly. Ask her to answer with just yes or no, then call this tool again.", 400);
    }
    const result = await ctx.runMutation(internal.voice.decide, {
      profileId,
      subject: subject as "refund" | "document" | "group",
      yes: YES.includes(said),
    });
    return text(`${result} Read that back to her, then ask if there is anything else.`);
  }),
});

http.route({
  path: "/cartesia/student-call",
  method: "POST",
  handler: httpAction(async (ctx, req) => {
    if (!authorized(req)) return text("Unauthorized.", 401);
    const body = await readObject(req);
    const profileId = body && field(body, "profile_id", "profileId");
    const summary = body && field(body, "summary");
    if (!profileId || !summary) return text("Need profile_id and summary.", 400);
    const direction = (body && field(body, "direction")) === "inbound" ? "inbound" : "outbound";
    await ctx.runMutation(internal.voice.logCall, {
      profileId,
      direction,
      purpose: (body && field(body, "purpose")) ?? "student_call",
      summary,
      ...(body && field(body, "notification_id", "notificationId")
        ? { notificationId: field(body, "notification_id", "notificationId") }
        : {}),
    });
    return text("Recorded. Thank her and end the call.");
  }),
});

export default http;
