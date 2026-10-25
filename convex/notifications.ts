import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

// The message layer. Every agent that wants to tell the student something writes one row here
// instead of reaching for a channel itself; a deliverer picks it up and sends it.
//
//   agent ──> notifications:queue ──> state "queued"
//                                       │  Coordinator       -> ASI:One chat
//                                       │  agents/voice      -> a Cartesia phone call
//                                       │  agents/notify/sms -> SMS, when a sender is configured
//                                       ▼  the dashboard renders every row as one thread
//                                     "sent" -> "delivered" -> "acknowledged"
//
// The body is rendered and checked before it gets here (agents/guard.py), so a deliverer never
// edits the text; it only moves it.

const CHANNEL = v.union(v.literal("chat"), v.literal("voice"), v.literal("sms"), v.literal("inapp"));
const AWAITING = v.union(v.literal("approval"), v.literal("group_optin"), v.literal("none"));

export const queue = mutation({
  args: {
    profileId: v.id("profiles"),
    channel: CHANNEL,
    kind: v.string(),
    title: v.string(),
    body: v.string(),
    refs: v.optional(v.array(v.string())),
    awaiting: v.optional(AWAITING),
  },
  handler: async (ctx, args) => {
    // The same news from two triggers (a rule re-run and a proactive sweep) is one message, not two.
    const recent = await ctx.db
      .query("notifications")
      .withIndex("by_profile_and_channel", (q) => q.eq("profileId", args.profileId).eq("channel", args.channel))
      .order("desc")
      .take(25);
    const same = recent.find(
      (n) => n.kind === args.kind && n.body === args.body && n.state !== "failed",
    );
    if (same) return same._id;
    const id = await ctx.db.insert("notifications", {
      ...args,
      state: "queued",
      at: new Date().toISOString(),
    });
    await ctx.db.insert("activity", {
      agent: "notify",
      action: "notification_queued",
      detail: `${args.channel}: ${args.title}`,
      inputIds: args.refs ?? [],
      outputIds: [id],
      at: new Date().toISOString(),
    });
    return id;
  },
});

// What a deliverer should send next on its channel, oldest first.
export const pending = query({
  args: { channel: CHANNEL, limit: v.optional(v.number()) },
  handler: async (ctx, { channel, limit }) => {
    const rows = await ctx.db
      .query("notifications")
      .withIndex("by_state", (q) => q.eq("state", "queued"))
      .take(100);
    return rows.filter((n) => n.channel === channel).slice(0, limit ?? 10);
  },
});

export const markSent = mutation({
  args: { notificationId: v.id("notifications"), error: v.optional(v.string()) },
  handler: async (ctx, { notificationId, error }) => {
    const n = await ctx.db.get(notificationId);
    if (n === null) throw new Error(`notification ${notificationId} not found`);
    const now = new Date().toISOString();
    await ctx.db.patch("notifications", notificationId,
      error ? { state: "failed", error, sentAt: now } : { state: "sent", sentAt: now });
    await ctx.db.insert("activity", {
      agent: "notify",
      action: error ? "notification_failed" : "notification_sent",
      detail: error ? `${n.channel}: ${n.title} could not be sent (${error})` : `${n.channel}: ${n.title}`,
      inputIds: [notificationId],
      at: now,
    });
  },
});

// The student replied: a tap on a card, a YES on the phone, a button on the dashboard.
export const acknowledge = mutation({
  args: { notificationId: v.id("notifications"), answer: v.optional(v.string()) },
  handler: async (ctx, { notificationId, answer }) => {
    const n = await ctx.db.get(notificationId);
    if (n === null) throw new Error(`notification ${notificationId} not found`);
    const now = new Date().toISOString();
    await ctx.db.patch("notifications", notificationId,
      { state: "acknowledged", ackedAt: now, ...(answer ? { answer } : {}) });
    await ctx.db.insert("activity", {
      agent: "notify",
      action: "notification_acknowledged",
      detail: `${n.title}${answer ? `: ${answer}` : ""}`,
      inputIds: [notificationId],
      at: now,
    });
  },
});

// The thread the dashboard shows, and what a phone call reads out: newest first.
export const forProfile = query({
  args: { profileId: v.id("profiles"), limit: v.optional(v.number()) },
  handler: async (ctx, { profileId, limit }) => {
    return await ctx.db
      .query("notifications")
      .withIndex("by_profile", (q) => q.eq("profileId", profileId))
      .order("desc")
      .take(limit ?? 50);
  },
});

// Anything still waiting on the student, for the inbound call and the dashboard banner.
export const awaitingAnswer = query({
  args: { profileId: v.id("profiles") },
  handler: async (ctx, { profileId }) => {
    const rows = await ctx.db
      .query("notifications")
      .withIndex("by_profile", (q) => q.eq("profileId", profileId))
      .order("desc")
      .take(50);
    return rows.filter((n) => n.awaiting !== undefined && n.awaiting !== "none" && n.state !== "acknowledged");
  },
});
