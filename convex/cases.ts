import { mutation, query } from "./_generated/server";
import type { MutationCtx } from "./_generated/server";
import type { Id } from "./_generated/dataModel";
import { v } from "convex/values";

// The Caseworker state machine. Every state change goes through transition(), so the
// Coordinator, the Cartesia webhook and the Ledger's refund match all obey the same rules.
const NEXT: Record<string, string[]> = {
  open: ["awaiting_approval"],
  awaiting_approval: ["contacting_employer", "closed"],
  contacting_employer: ["awaiting_response", "escalate_irs"],
  awaiting_response: ["refund_received", "contacting_employer", "escalate_irs"],
  refund_received: ["closed"],
  escalate_irs: ["closed"],
  closed: [],
};

const IRS_CHECKLIST =
  "Payroll refused the refund. Next steps: 1) Ask payroll for a written statement that they will not refund. " +
  "2) Fill out Form 843 (Claim for Refund and Request for Abatement) and Form 8316. 3) Attach your W-2, visa, " +
  "I-94, I-20, and the employer's statement (or a note that you could not get one). " +
  "4) Mail to the IRS address in the Form 843 instructions. Confirm with your school's international office.";

const DAY = 24 * 60 * 60 * 1000;
const inDays = (n: number) => new Date(Date.now() + n * DAY).toISOString().slice(0, 10);

async function transition(
  ctx: MutationCtx,
  caseId: Id<"cases">,
  to: string,
  detail: string,
  fields: { nextFollowUp?: string; outcome?: string } = {},
  requireState?: string,
) {
  const c = await ctx.db.get(caseId);
  if (c === null) throw new Error(`case ${caseId} not found`);
  if (requireState && c.state !== requireState) throw new Error(`case is ${c.state}, not ${requireState}`);
  if (!NEXT[c.state]?.includes(to)) throw new Error(`case cannot move from ${c.state} to ${to}`);
  await ctx.db.patch("cases", caseId, { state: to, ...fields });
  await ctx.db.insert("activity", {
    agent: "caseworker",
    action: `case_${to}`,
    detail,
    inputIds: [caseId],
    at: new Date().toISOString(),
  });
}

export const get = query({
  args: { caseId: v.id("cases") },
  handler: async (ctx, { caseId }) => {
    return await ctx.db.get(caseId);
  },
});

export const listByProfile = query({
  args: { profileId: v.id("profiles") },
  handler: async (ctx, { profileId }) => {
    return await ctx.db
      .query("cases")
      .withIndex("by_profile", (q) => q.eq("profileId", profileId))
      .take(50);
  },
});

// Opens a case for a flag with its draft request, ready for the student's approval.
// One case per flag: opening again returns the existing case.
export const open = mutation({
  args: { flagId: v.id("flags"), profileId: v.id("profiles"), amountCents: v.number(), draft: v.string() },
  handler: async (ctx, args) => {
    const existing = await ctx.db
      .query("cases")
      .withIndex("by_flag", (q) => q.eq("flagId", args.flagId))
      .first();
    if (existing) return existing._id;
    const caseId = await ctx.db.insert("cases", { ...args, state: "open", nextFollowUp: inDays(1) });
    await ctx.db.patch("flags", args.flagId, { status: "case_opened" });
    await ctx.db.insert("activity", {
      agent: "caseworker",
      action: "case_open",
      detail: `Refund case opened for $${(args.amountCents / 100).toFixed(2)}`,
      inputIds: [args.flagId],
      outputIds: [caseId],
      at: new Date().toISOString(),
    });
    await transition(ctx, caseId, "awaiting_approval", "Draft request written; waiting for the student's approval");
    return caseId;
  },
});

export const approve = mutation({
  args: { caseId: v.id("cases") },
  handler: async (ctx, { caseId }) => {
    await transition(ctx, caseId, "contacting_employer", "Student approved; contacting payroll", {
      nextFollowUp: inDays(1),
    }, "awaiting_approval");
  },
});

export const decline = mutation({
  args: { caseId: v.id("cases") },
  handler: async (ctx, { caseId }) => {
    await transition(ctx, caseId, "closed", "Student declined contacting payroll", { outcome: "declined_by_student" }, "awaiting_approval");
  },
});

// Called by the Cartesia log_call_outcome webhook (Person 3).
export const logCallOutcome = mutation({
  args: {
    caseId: v.id("cases"),
    answeredBy: v.string(),
    summary: v.string(),
    result: v.union(v.literal("promised"), v.literal("refused"), v.literal("needs_student")),
    promisedBy: v.optional(v.string()),
    referenceNo: v.optional(v.string()),
    transcriptUrl: v.optional(v.string()),
  },
  handler: async (ctx, { caseId, result, ...call }) => {
    const callId = await ctx.db.insert("calls", { caseId, ...call, at: new Date().toISOString() });
    if (result === "refused") {
      await transition(ctx, caseId, "escalate_irs", `Payroll refused (call ${callId}); IRS checklist prepared`, {
        outcome: IRS_CHECKLIST,
      });
    } else if (result === "needs_student") {
      await transition(ctx, caseId, "awaiting_response", "Payroll needs the student on the line; three-way call to schedule", {
        nextFollowUp: inDays(2),
      });
    } else {
      await transition(ctx, caseId, "awaiting_response", `Payroll promised a refund by ${call.promisedBy ?? "an unstated date"}`, {
        nextFollowUp: call.promisedBy ?? inDays(14),
      });
    }
    return callId;
  },
});

// Called by the Ledger when a deposit matches the case amount from the employer.
export const refundReceived = mutation({
  args: { caseId: v.id("cases"), transactionId: v.id("transactions") },
  handler: async (ctx, { caseId, transactionId }) => {
    await transition(ctx, caseId, "refund_received", `Refund deposit ${transactionId} matched`);
    const c = await ctx.db.get(caseId);
    await ctx.db.patch("flags", c!.flagId, { status: "resolved" });
    await transition(ctx, caseId, "closed", "Refund received; case closed", { outcome: "refunded" });
  },
});

// ---- Payroll call through Cartesia (agents/caseworker/cartesia.py) ----
// Any approval (ASI:One reply or the dashboard button) moves a case to contacting_employer.
// The Caseworker claims each such case exactly once, so one approval places exactly one call.

export const awaitingCall = query({
  args: {},
  handler: async (ctx) => {
    const rows = await ctx.db
      .query("cases")
      .withIndex("by_state", (q) => q.eq("state", "contacting_employer"))
      .take(20);
    return rows.filter((c) => c.callRequestedAt === undefined);
  },
});

// Returns true only for the first caller; everyone else sees the claim and skips the call.
export const claimCall = mutation({
  args: { caseId: v.id("cases") },
  handler: async (ctx, { caseId }) => {
    const c = await ctx.db.get(caseId);
    if (c === null || c.state !== "contacting_employer" || c.callRequestedAt !== undefined) return false;
    await ctx.db.patch("cases", caseId, { callRequestedAt: new Date().toISOString() });
    return true;
  },
});

export const recordCallStart = mutation({
  args: { caseId: v.id("cases"), callRequestId: v.optional(v.string()), error: v.optional(v.string()) },
  handler: async (ctx, { caseId, callRequestId, error }) => {
    await ctx.db.patch("cases", caseId, error ? { callError: error } : { callRequestId });
    await ctx.db.insert("activity", {
      agent: "voice",
      action: error ? "call_failed" : "call_placed",
      detail: error ? `Payroll call could not start: ${error}` : `Calling payroll through Cartesia (call ${callRequestId}). The agent says it is an AI assistant acting with the student's permission.`,
      inputIds: [caseId],
      at: new Date().toISOString(),
    });
  },
});
