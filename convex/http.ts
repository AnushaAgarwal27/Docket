import { httpRouter } from "convex/server";
import { env, httpAction } from "./_generated/server";
import { api, internal } from "./_generated/api";

// Webhook tools for the Cartesia voice agent that calls payroll (see docs/CARTESIA.md).
//   POST /cartesia/case-summary   body {case_id}                      -> plain-text facts for the call
//   POST /cartesia/call-outcome   body {case_id, result, answered_by,  -> runs cases.logCallOutcome
//                                       summary, promised_by?, reference_number?}
//   result is one of promised, stalled, refused, needs_student
// Both require "Authorization: Bearer <CARTESIA_TOOL_TOKEN>". Responses are short plain text because
// Cartesia hands the body to the voice model as the tool result.

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

export default http;
