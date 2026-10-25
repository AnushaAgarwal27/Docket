import { mutation, query } from "./_generated/server";
import { v } from "convex/values";
import schema from "./schema";

// The Hearing: Tax (advocate) and Auditor argue a finding before it reaches the student.
// The Auditor records the outcome here; the verdict also sets the flag's status, which decides
// whether the Caseworker may open a case on its own.
const STATUS_FOR_VERDICT = {
  upheld: "open",
  downgraded: "needs_student_ok",
  needs_human: "needs_review",
  defeated: "defeated",
} as const;
// Statuses a hearing may change; once a case is opened or resolved, a re-hearing leaves the flag alone.
const CONTESTABLE = ["contested", "open", "needs_student_ok", "needs_review", "defeated"];

export const record = mutation({
  args: schema.tables.hearings.validator.omit("createdAt").fields,
  handler: async (ctx, args) => {
    const hearingId = await ctx.db.insert("hearings", { ...args, createdAt: new Date().toISOString() });
    if (args.flagId) {
      const flag = await ctx.db.get(args.flagId);
      if (flag && CONTESTABLE.includes(flag.status)) {
        await ctx.db.patch("flags", args.flagId, { status: STATUS_FOR_VERDICT[args.verdict] });
      }
    }
    await ctx.db.insert("activity", {
      agent: "auditor",
      action: `verdict_${args.verdict}`,
      detail: `${args.ruleId}: ${args.verdict}. ${args.reason}`.slice(0, 300),
      inputIds: args.flagId ? [args.flagId] : [args.profileId],
      outputIds: [hearingId],
      at: new Date().toISOString(),
    });
    return hearingId;
  },
});

// The most recent hearings for a student, newest first (for "why?" and the dashboard).
export const latestForProfile = query({
  args: { profileId: v.id("profiles"), limit: v.optional(v.number()) },
  handler: async (ctx, { profileId, limit }) => {
    return await ctx.db
      .query("hearings")
      .withIndex("by_profile", (q) => q.eq("profileId", profileId))
      .order("desc")
      .take(limit ?? 10);
  },
});

export const latestForFlag = query({
  args: { flagId: v.id("flags") },
  handler: async (ctx, { flagId }) => {
    return await ctx.db
      .query("hearings")
      .withIndex("by_flag", (q) => q.eq("flagId", flagId))
      .order("desc")
      .first();
  },
});
