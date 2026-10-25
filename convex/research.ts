import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

// What the Athena research agent found (agents/researcher). Two kinds:
//   watch  the agent scanned news and official pages on its own and found something that changes
//          what this student should do
//   ask    the student asked a question, on the phone or in chat, and the agent researched it
//
// Every row keeps its sources. The answer text was written by the research layer and then checked
// by agents/guard.py before it got here, so nothing further rewrites it.

const SOURCE = v.object({
  title: v.string(),
  url: v.string(),
  publishedAt: v.optional(v.string()),
  excerpt: v.optional(v.string()),
});

export const record = mutation({
  args: {
    profileId: v.optional(v.id("profiles")),
    kind: v.union(v.literal("watch"), v.literal("ask")),
    topic: v.string(),
    question: v.optional(v.string()),
    answer: v.string(),
    sources: v.array(SOURCE),
    engine: v.string(),
    confidence: v.union(v.literal("high"), v.literal("medium"), v.literal("low")),
    actionable: v.boolean(),
  },
  handler: async (ctx, args) => {
    const now = new Date().toISOString();
    const id = await ctx.db.insert("research", { ...args, createdAt: now });
    await ctx.db.insert("activity", {
      agent: "researcher",
      action: args.kind === "ask" ? "research_answered" : "research_found",
      detail: `${args.topic} (${args.engine}, ${args.confidence} confidence, ${args.sources.length} sources)`,
      inputIds: args.profileId ? [args.profileId] : [],
      outputIds: [id],
      at: now,
    });
    return id;
  },
});

export const markNotified = mutation({
  args: { researchId: v.id("research") },
  handler: async (ctx, { researchId }) => {
    await ctx.db.patch("research", researchId, { notifiedAt: new Date().toISOString() });
  },
});

export const forProfile = query({
  args: { profileId: v.id("profiles"), limit: v.optional(v.number()) },
  handler: async (ctx, { profileId, limit }) => {
    const mine = await ctx.db
      .query("research")
      .withIndex("by_profile", (q) => q.eq("profileId", profileId))
      .order("desc")
      .take(limit ?? 25);
    // Findings that apply to every F-1 student are stored without a profile.
    const watch = await ctx.db
      .query("research")
      .withIndex("by_kind", (q) => q.eq("kind", "watch"))
      .order("desc")
      .take(50);
    const everyone = watch.filter((r) => r.profileId === undefined);
    return [...mine, ...everyone]
      .sort((a, b) => b.createdAt.localeCompare(a.createdAt))
      .slice(0, limit ?? 25);
  },
});

// Actionable watch findings nobody has told the student about yet.
export const unnotified = query({
  args: { limit: v.optional(v.number()) },
  handler: async (ctx, { limit }) => {
    const rows = await ctx.db
      .query("research")
      .withIndex("by_kind", (q) => q.eq("kind", "watch"))
      .order("desc")
      .take(50);
    return rows.filter((r) => r.actionable && r.notifiedAt === undefined).slice(0, limit ?? 10);
  },
});

// The latest answer to a question, so a repeated question on a call does not re-run the research.
export const latestAnswer = query({
  args: { profileId: v.id("profiles") },
  handler: async (ctx, { profileId }) => {
    const rows = await ctx.db
      .query("research")
      .withIndex("by_profile", (q) => q.eq("profileId", profileId))
      .order("desc")
      .take(10);
    return rows.find((r) => r.kind === "ask") ?? null;
  },
});
