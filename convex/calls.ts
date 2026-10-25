import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

// Calls that are not about a refund case: Docket phoning the student about a finding, and the
// student phoning Docket's line and asking something. Payroll calls still go through
// cases:logCallOutcome, which owns the case state machine.

export const logStudentCall = mutation({
  args: {
    profileId: v.id("profiles"),
    direction: v.union(v.literal("outbound"), v.literal("inbound")),
    purpose: v.string(),
    summary: v.string(),
    answeredBy: v.optional(v.string()),
    toNumber: v.optional(v.string()),
    callRequestId: v.optional(v.string()),
    transcriptUrl: v.optional(v.string()),
  },
  handler: async (ctx, { profileId, direction, purpose, summary, answeredBy, ...rest }) => {
    const now = new Date().toISOString();
    const id = await ctx.db.insert("calls", {
      profileId, direction, purpose, summary,
      answeredBy: answeredBy ?? "The student",
      at: now,
      ...rest,
    });
    await ctx.db.insert("activity", {
      agent: "voice",
      action: direction === "inbound" ? "student_called_in" : "student_called",
      detail: `${purpose.replace(/_/g, " ")}: ${summary}`,
      inputIds: [profileId],
      outputIds: [id],
      at: now,
    });
    return id;
  },
});

export const forProfile = query({
  args: { profileId: v.id("profiles"), limit: v.optional(v.number()) },
  handler: async (ctx, { profileId, limit }) => {
    return await ctx.db
      .query("calls")
      .withIndex("by_profile", (q) => q.eq("profileId", profileId))
      .order("desc")
      .take(limit ?? 25);
  },
});
