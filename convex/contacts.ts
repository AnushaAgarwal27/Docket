import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

// Who Docket can call. Payroll and the school are seeded; legal aid and attorneys are found by the
// research agent (agents/researcher) from official and public pages.
//
// `verified` is true only when the number came from a page the code fetched and stored, never from a
// model's memory. An unverified contact is shown to the student but is never dialled on its own.
//
// Demo safety: agents/voice/calls.py redirects every outbound call to DEMO_CALL_NUMBER, so the numbers
// here are what the call *says* it is reaching, not what rings, until the demo redirect is turned off.

const ROLE = v.union(v.literal("payroll"), v.literal("irs"), v.literal("school"),
                     v.literal("legal_aid"), v.literal("attorney"));

export const upsert = mutation({
  args: {
    name: v.string(),
    org: v.string(),
    role: ROLE,
    phone: v.string(),
    email: v.optional(v.string()),
    url: v.optional(v.string()),
    foundBy: v.union(v.literal("seed"), v.literal("research")),
    verified: v.boolean(),
    note: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    const same = await ctx.db
      .query("contacts")
      .withIndex("by_role", (q) => q.eq("role", args.role))
      .take(50);
    const existing = same.find((c) => c.org === args.org && c.name === args.name);
    if (existing) {
      await ctx.db.patch("contacts", existing._id, args);
      return existing._id;
    }
    const id = await ctx.db.insert("contacts", { ...args, createdAt: new Date().toISOString() });
    await ctx.db.insert("activity", {
      agent: args.foundBy === "research" ? "researcher" : "seed",
      action: "contact_recorded",
      detail: `${args.role}: ${args.name} at ${args.org}${args.verified ? " (verified from an official page)" : " (unverified)"}`,
      outputIds: [id],
      at: new Date().toISOString(),
    });
    return id;
  },
});

export const byRole = query({
  args: { role: ROLE },
  handler: async (ctx, { role }) => {
    return await ctx.db.query("contacts").withIndex("by_role", (q) => q.eq("role", role)).take(25);
  },
});

export const list = query({
  args: {},
  handler: async (ctx) => {
    return await ctx.db.query("contacts").order("desc").take(50);
  },
});
