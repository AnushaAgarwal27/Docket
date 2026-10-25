import { mutation, query } from "./_generated/server";
import type { MutationCtx, QueryCtx } from "./_generated/server";
import type { Doc, Id } from "./_generated/dataModel";
import { v } from "convex/values";

// Group cases. When several students at one employer get the same finding, it is a payroll setup
// problem, not a one-off, and the students are far stronger asking together. convex/patterns.ts
// already counts the pattern; this module turns a pattern into a group, invites every flagged
// student, and keeps the combined ask.
//
// Two rules the whole feature rests on:
//   1. A student is only ever in the combined request after they said yes. "invited" is not "joined".
//   2. The combined total is recomputed from joined members, never typed in and never estimated.

const MIN_MEMBERS = 3;

function totals(members: Doc<"groupMembers">[]) {
  const joined = members.filter((m) => m.state === "joined");
  return { joinedCount: joined.length, joinedCents: joined.reduce((s, m) => s + m.amountCents, 0) };
}

async function recount(ctx: MutationCtx, groupId: Id<"groups">) {
  const members = await ctx.db
    .query("groupMembers")
    .withIndex("by_group", (q) => q.eq("groupId", groupId))
    .take(200);
  await ctx.db.patch("groups", groupId, totals(members));
  return totals(members);
}

// Every student who has the same finding at the same employer, with the flag and amount that would
// go into a combined request. This is what the Organizer pattern-matches on: it is computed from
// flags the rules engine wrote, never from a model's reading of the data.
export const candidates = query({
  args: { ruleId: v.string() },
  handler: async (ctx, { ruleId }) => {
    const profiles = await ctx.db.query("profiles").take(100);
    const byEmployer = new Map<string, { profileId: Id<"profiles">; flagId: Id<"flags">; amountCents: number;
                                         name: string; simulated: boolean }[]>();
    for (const p of profiles) {
      const flags = await ctx.db
        .query("flags").withIndex("by_profile", (q) => q.eq("profileId", p._id)).take(50);
      const flag = flags.find((f) => f.ruleId === ruleId && f.status !== "resolved");
      if (flag === undefined) continue;
      const stubs = await ctx.db
        .query("paystubs").withIndex("by_profile", (q) => q.eq("profileId", p._id)).take(100);
      // The employer on the paystubs the rule actually hit on, not whatever is typed on the profile.
      const linked = new Set(flag.paystubIds ?? []);
      const employers = new Set(stubs.filter((s) => linked.size === 0 || linked.has(s._id)).map((s) => s.employer));
      for (const employer of employers) {
        const list = byEmployer.get(employer) ?? [];
        list.push({ profileId: p._id, flagId: flag._id, amountCents: flag.amountCents,
                    name: p.name, simulated: p.simulated === true });
        byEmployer.set(employer, list);
      }
    }
    return [...byEmployer.entries()]
      .map(([employer, members]) => ({
        employer,
        members,
        flagged: members.length,
        totalCents: members.reduce((s, m) => s + m.amountCents, 0),
        pattern: members.length >= MIN_MEMBERS,
      }))
      .filter((row) => row.pattern)
      .sort((a, b) => b.flagged - a.flagged);
  },
});

// Called by the Organizer once it has found a pattern. Returns the group and the students who
// still need to be asked. Safe to call repeatedly: an existing group is reused and only students
// who are not members yet are invited.
export const formFromPattern = mutation({
  args: {
    employer: v.string(),
    ruleId: v.string(),
    summary: v.string(),
    members: v.array(v.object({
      profileId: v.id("profiles"),
      flagId: v.id("flags"),
      amountCents: v.number(),
    })),
  },
  handler: async (ctx, { employer, ruleId, summary, members }) => {
    if (members.length < MIN_MEMBERS) {
      throw new Error(`a group needs at least ${MIN_MEMBERS} flagged students, got ${members.length}`);
    }
    const now = new Date().toISOString();
    const existing = await ctx.db
      .query("groups")
      .withIndex("by_employer_and_rule", (q) => q.eq("employer", employer).eq("ruleId", ruleId))
      .first();
    const groupId = existing?._id ?? (await ctx.db.insert("groups", {
      employer, ruleId, summary, state: "forming", threshold: MIN_MEMBERS,
      joinedCount: 0, joinedCents: 0, createdAt: now,
    }));
    if (existing) await ctx.db.patch("groups", groupId, { summary });
    else {
      await ctx.db.insert("activity", {
        agent: "organizer",
        action: "group_formed",
        detail: `${members.length} students at ${employer} have the same ${ruleId} finding; group case opened`,
        outputIds: [groupId],
        at: now,
      });
    }
    const already = await ctx.db
      .query("groupMembers")
      .withIndex("by_group", (q) => q.eq("groupId", groupId))
      .take(200);
    const known = new Set(already.map((m) => m.profileId));
    const invited: Id<"profiles">[] = [];
    for (const m of members) {
      if (known.has(m.profileId)) continue;
      await ctx.db.insert("groupMembers", { groupId, ...m, state: "invited", invitedAt: now });
      invited.push(m.profileId);
    }
    await recount(ctx, groupId);
    return { groupId, invited };
  },
});

// The student's answer. Comes from a card, the dashboard or a phone call; all three land here.
export const respond = mutation({
  args: { groupId: v.id("groups"), profileId: v.id("profiles"), join: v.boolean(), via: v.optional(v.string()) },
  handler: async (ctx, { groupId, profileId, join, via }) => {
    const member = await ctx.db
      .query("groupMembers")
      .withIndex("by_group_and_profile", (q) => q.eq("groupId", groupId).eq("profileId", profileId))
      .unique();
    if (member === null) throw new Error("this student was not invited to that group");
    if (member.state !== "invited") return member.state;
    const now = new Date().toISOString();
    await ctx.db.patch("groupMembers", member._id, {
      state: join ? "joined" : "declined",
      decidedAt: now,
    });
    const after = await recount(ctx, groupId);
    const group = await ctx.db.get(groupId);
    await ctx.db.insert("activity", {
      agent: "organizer",
      action: join ? "group_joined" : "group_declined",
      detail: join
        ? `A student joined the ${group?.employer} group case${via ? ` (${via})` : ""}; ` +
          `${after.joinedCount} joined, $${(after.joinedCents / 100).toFixed(2)} combined`
        : `A student declined the ${group?.employer} group case${via ? ` (${via})` : ""}; their own case is unaffected`,
      inputIds: [groupId, profileId],
      at: now,
    });
    // Once anyone has joined the group is real; the Organizer can act for the joined members.
    if (join && group?.state === "forming") {
      await ctx.db.patch("groups", groupId, { state: "open", openedAt: now });
    }
    return join ? "joined" : "declined";
  },
});

export const setState = mutation({
  args: {
    groupId: v.id("groups"),
    state: v.union(v.literal("forming"), v.literal("open"), v.literal("contacting"), v.literal("closed")),
    note: v.optional(v.string()),
  },
  handler: async (ctx, { groupId, state, note }) => {
    await ctx.db.patch("groups", groupId, { state, ...(note ? { caseNote: note } : {}) });
    await ctx.db.insert("activity", {
      agent: "organizer",
      action: `group_${state}`,
      detail: note ?? `Group case is now ${state}`,
      inputIds: [groupId],
      at: new Date().toISOString(),
    });
  },
});

export const attachContact = mutation({
  args: { groupId: v.id("groups"), contactId: v.id("contacts") },
  handler: async (ctx, { groupId, contactId }) => {
    await ctx.db.patch("groups", groupId, { contactId });
  },
});

async function hydrate(ctx: QueryCtx, group: Doc<"groups">) {
  const members = await ctx.db
    .query("groupMembers")
    .withIndex("by_group", (q) => q.eq("groupId", group._id))
    .take(200);
  const withNames = await Promise.all(members.map(async (m) => {
    const p = await ctx.db.get(m.profileId);
    return { ...m, name: p?.name ?? "Unknown student", simulated: p?.simulated === true };
  }));
  const contact = group.contactId ? await ctx.db.get(group.contactId) : null;
  return { ...group, members: withNames, contact };
}

export const list = query({
  args: {},
  handler: async (ctx) => {
    const groups = await ctx.db.query("groups").order("desc").take(20);
    return await Promise.all(groups.map((g) => hydrate(ctx, g)));
  },
});

export const get = query({
  args: { groupId: v.id("groups") },
  handler: async (ctx, { groupId }) => {
    const g = await ctx.db.get(groupId);
    return g === null ? null : await hydrate(ctx, g);
  },
});

// Every group this student is in, with their own membership state. Drives the dashboard card,
// the ASI:One invite and the phone call.
export const forProfile = query({
  args: { profileId: v.id("profiles") },
  handler: async (ctx, { profileId }) => {
    const mine = await ctx.db
      .query("groupMembers")
      .withIndex("by_profile", (q) => q.eq("profileId", profileId))
      .take(20);
    const out = [];
    for (const m of mine) {
      const group = await ctx.db.get(m.groupId);
      if (group === null) continue;
      out.push({ membership: m, group });
    }
    return out;
  },
});

// The one invitation still waiting on this student, for a call or a chat to put to them.
export const pendingInvite = query({
  args: { profileId: v.id("profiles") },
  handler: async (ctx, { profileId }) => {
    const mine = await ctx.db
      .query("groupMembers")
      .withIndex("by_profile", (q) => q.eq("profileId", profileId))
      .take(20);
    const invited = mine.filter((m) => m.state === "invited")
      .sort((a, b) => a.invitedAt.localeCompare(b.invitedAt))[0];
    if (invited === undefined) return null;
    const group = await ctx.db.get(invited.groupId);
    if (group === null) return null;
    const members = await ctx.db
      .query("groupMembers")
      .withIndex("by_group", (q) => q.eq("groupId", group._id))
      .take(200);
    return { membership: invited, group, inviteeCount: members.length };
  },
});
