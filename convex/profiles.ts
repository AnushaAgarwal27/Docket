import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

export const get = query({
  args: { profileId: v.id("profiles") },
  handler: async (ctx, { profileId }) => {
    return await ctx.db.get(profileId);
  },
});

export const list = query({
  args: {},
  handler: async (ctx) => {
    return await ctx.db.query("profiles").take(20);
  },
});

// The profile form card (ASI:One). Only the fields the student filled in are changed; the Coordinator
// validates the values in code before calling this.
export const updateFromForm = mutation({
  args: {
    profileId: v.id("profiles"),
    arrivalDate: v.optional(v.string()),
    visa: v.optional(v.string()),
    employer: v.optional(v.string()),
    employmentType: v.optional(v.union(v.literal("employee"), v.literal("contractor"))),
    employerIsSchool: v.optional(v.boolean()),
    enrolled: v.optional(v.boolean()),
  },
  handler: async (ctx, { profileId, ...fields }) => {
    const changes = Object.fromEntries(Object.entries(fields).filter(([, value]) => value !== undefined));
    await ctx.db.patch("profiles", profileId, changes);
    await ctx.db.insert("activity", {
      agent: "coordinator",
      action: "profile_updated",
      detail: `Profile updated from the form: ${Object.keys(changes).join(", ") || "no changes"}`,
      inputIds: [profileId],
      at: new Date().toISOString(),
    });
    return Object.keys(changes);
  },
});
