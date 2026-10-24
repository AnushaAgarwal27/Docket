import { query } from "./_generated/server";
import { v } from "convex/values";

// Everything the live dashboard shows for one student, in one reactive query.
export const snapshot = query({
  args: { profileId: v.id("profiles") },
  handler: async (ctx, { profileId }) => {
    const profile = await ctx.db.get(profileId);
    if (profile === null) return null;
    const flags = await ctx.db
      .query("flags")
      .withIndex("by_profile", (q) => q.eq("profileId", profileId))
      .take(50);
    const flagsWithSource = await Promise.all(
      flags.map(async (f) => {
        const source = await ctx.db.get(f.sourceId);
        return { ...f, sourceTitle: source?.title ?? null, sourceUrl: source?.url ?? null };
      }),
    );
    const cases = await ctx.db
      .query("cases")
      .withIndex("by_profile", (q) => q.eq("profileId", profileId))
      .take(50);
    const casesWithCalls = await Promise.all(
      cases.map(async (c) => ({
        ...c,
        calls: await ctx.db
          .query("calls")
          .withIndex("by_case", (q) => q.eq("caseId", c._id))
          .order("desc")
          .take(10),
      })),
    );
    const paystubs = await ctx.db
      .query("paystubs")
      .withIndex("by_profile", (q) => q.eq("profileId", profileId))
      .take(100);
    const transactions = await ctx.db
      .query("transactions")
      .withIndex("by_profile", (q) => q.eq("profileId", profileId))
      .order("desc")
      .take(50);
    return { profile, flags: flagsWithSource, cases: casesWithCalls, paystubs, transactions };
  },
});
