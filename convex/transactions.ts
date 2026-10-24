import { mutation, query } from "./_generated/server";
import { v } from "convex/values";
import schema from "./schema";

// Ledger writes every Nessie row here. Nessie's id is the key, so re-polling never duplicates.
export const upsert = mutation({
  args: schema.tables.transactions.validator.fields,
  handler: async (ctx, args) => {
    const existing = await ctx.db
      .query("transactions")
      .withIndex("by_nessie", (q) => q.eq("nessieId", args.nessieId))
      .unique();
    if (existing) return { id: existing._id, created: false };
    return { id: await ctx.db.insert("transactions", args), created: true };
  },
});

export const listByProfile = query({
  args: { profileId: v.id("profiles") },
  handler: async (ctx, { profileId }) => {
    return await ctx.db
      .query("transactions")
      .withIndex("by_profile", (q) => q.eq("profileId", profileId))
      .take(1000);
  },
});
