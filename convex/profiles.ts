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

// Who Cartesia's inbound line is talking to. Looked up by the number that called in.
export const byPhone = query({
  args: { phone: v.string() },
  handler: async (ctx, { phone }) => {
    return await ctx.db.query("profiles").withIndex("by_phone", (q) => q.eq("phone", phone)).first();
  },
});

// How Docket may reach the student. Nothing is dialled or texted without the matching consent,
// so turning a channel off here stops it everywhere.
export const setContact = mutation({
  args: {
    profileId: v.id("profiles"),
    phone: v.optional(v.string()),
    voiceConsent: v.optional(v.boolean()),
    smsConsent: v.optional(v.boolean()),
    groupPreference: v.optional(v.union(v.literal("ask"), v.literal("always"), v.literal("never"))),
  },
  handler: async (ctx, { profileId, ...fields }) => {
    const changes = Object.fromEntries(Object.entries(fields).filter(([, value]) => value !== undefined));
    if (Object.keys(changes).length === 0) return [];
    await ctx.db.patch("profiles", profileId, changes);
    const said = Object.entries(changes)
      .map(([k, value]) => (k === "phone" ? "phone number" : `${k}: ${String(value)}`))
      .join(", ");
    await ctx.db.insert("activity", {
      agent: "coordinator",
      action: "contact_preferences_updated",
      detail: `Student set how Docket may reach her (${said})`,
      inputIds: [profileId],
      at: new Date().toISOString(),
    });
    return Object.keys(changes);
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
