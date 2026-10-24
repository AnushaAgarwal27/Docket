import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

export const listByProfile = query({
  args: { profileId: v.id("profiles") },
  handler: async (ctx, { profileId }) => {
    return await ctx.db
      .query("flags")
      .withIndex("by_profile", (q) => q.eq("profileId", profileId))
      .take(50);
  },
});

export const setStatus = mutation({
  args: { flagId: v.id("flags"), status: v.string() },
  handler: async (ctx, { flagId, status }) => {
    await ctx.db.patch("flags", flagId, { status });
  },
});

// Tax agent writes flags. One flag per rule per student; re-running the rules updates it.
export const upsert = mutation({
  args: {
    profileId: v.id("profiles"),
    ruleId: v.string(),
    amountCents: v.number(),
    explanation: v.string(),
    quote: v.string(),
    sourceId: v.id("sources"),
    status: v.string(),
  },
  handler: async (ctx, args) => {
    const existing = await ctx.db
      .query("flags")
      .withIndex("by_profile", (q) => q.eq("profileId", args.profileId))
      .take(50);
    const same = existing.find((f) => f.ruleId === args.ruleId);
    if (same) {
      // Keep a status that later agents moved forward (e.g. a case was opened).
      await ctx.db.patch("flags", same._id, { ...args, status: same.status });
      return same._id;
    }
    return await ctx.db.insert("flags", args);
  },
});
