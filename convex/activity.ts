import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

// Every agent writes one row per action, including actions it decided not to take.
export const log = mutation({
  args: {
    agent: v.string(),
    action: v.string(),
    detail: v.string(),
    sourceId: v.optional(v.id("sources")),
    inputIds: v.optional(v.array(v.string())),
    outputIds: v.optional(v.array(v.string())),
    kind: v.optional(v.string()),
    sender: v.optional(v.string()),
    receiver: v.optional(v.string()),
    summary: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    return await ctx.db.insert("activity", { ...args, at: new Date().toISOString() });
  },
});

// The dashboard feed: newest first.
export const recent = query({
  args: { limit: v.optional(v.number()) },
  handler: async (ctx, { limit }) => {
    return await ctx.db.query("activity").order("desc").take(limit ?? 50);
  },
});
