import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

export const getByUrl = query({
  args: { url: v.string() },
  handler: async (ctx, { url }) => {
    return await ctx.db
      .query("sources")
      .withIndex("by_url", (q) => q.eq("url", url))
      .unique();
  },
});

export const get = query({
  args: { sourceId: v.id("sources") },
  handler: async (ctx, { sourceId }) => {
    return await ctx.db.get(sourceId);
  },
});

// The source collector stores the exact fetched text. One row per URL; a re-fetch replaces it.
export const upsert = mutation({
  args: { url: v.string(), title: v.string(), text: v.string(), fetchedAt: v.string(), hash: v.string() },
  handler: async (ctx, args) => {
    const existing = await ctx.db
      .query("sources")
      .withIndex("by_url", (q) => q.eq("url", args.url))
      .unique();
    if (existing) {
      await ctx.db.replace("sources", existing._id, args);
      return existing._id;
    }
    return await ctx.db.insert("sources", args);
  },
});
