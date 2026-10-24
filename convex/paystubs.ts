import { mutation, query } from "./_generated/server";
import { v } from "convex/values";
import schema from "./schema";

export const listByProfile = query({
  args: { profileId: v.id("profiles") },
  handler: async (ctx, { profileId }) => {
    return await ctx.db
      .query("paystubs")
      .withIndex("by_profile", (q) => q.eq("profileId", profileId))
      .take(100);
  },
});

// Ledger writes paystubs. Re-recording the same source file updates it instead of duplicating.
export const record = mutation({
  args: schema.tables.paystubs.validator.fields,
  handler: async (ctx, args) => {
    const existing = await ctx.db
      .query("paystubs")
      .withIndex("by_profile", (q) => q.eq("profileId", args.profileId))
      .take(100);
    const same = existing.find((p) => p.sourceFile === args.sourceFile);
    if (same) {
      await ctx.db.replace("paystubs", same._id, args);
      return same._id;
    }
    return await ctx.db.insert("paystubs", args);
  },
});
