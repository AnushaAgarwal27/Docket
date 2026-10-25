import { query } from "./_generated/server";
import { v } from "convex/values";

// Everything the live dashboard shows for one student, in one reactive query.
export const snapshot = query({
  args: { profileId: v.id("profiles") },
  handler: async (ctx, { profileId }) => {
    const profile = await ctx.db.get(profileId);
    if (profile === null) return null;
    const flags = await ctx.db
      .query("flags")
      .withIndex("by_profile", (q) => q.eq("profileId", profileId))
      .take(50);
    const flagsWithSource = await Promise.all(
      flags.map(async (f) => {
        const source = await ctx.db.get(f.sourceId);
        return {
          ...f,
          sourceTitle: source?.title ?? null,
          sourceUrl: source?.url ?? null,
          // For the receipt: when the official text was stored and its hash, so a judge can see what was checked.
          sourceFetchedAt: source?.fetchedAt ?? null,
          sourceHash: source?.hash ?? null,
        };
      }),
    );
    const cases = await ctx.db
      .query("cases")
      .withIndex("by_profile", (q) => q.eq("profileId", profileId))
      .take(50);
    const casesWithCalls = await Promise.all(
      cases.map(async (c) => ({
        ...c,
        calls: await ctx.db
          .query("calls")
          .withIndex("by_case", (q) => q.eq("caseId", c._id))
          .order("desc")
          .take(10),
      })),
    );
    const paystubs = await ctx.db
      .query("paystubs")
      .withIndex("by_profile", (q) => q.eq("profileId", profileId))
      .take(100);
    const transactions = await ctx.db
      .query("transactions")
      .withIndex("by_profile", (q) => q.eq("profileId", profileId))
      .order("desc")
      .take(50);
    // The surfaces added for the voice, research, filing and group layers. Each is bounded and
    // comes from the same student file, so the dashboard still renders from one reactive query.
    const notifications = await ctx.db
      .query("notifications")
      .withIndex("by_profile", (q) => q.eq("profileId", profileId))
      .order("desc")
      .take(50);
    const documentRows = await ctx.db
      .query("documents")
      .withIndex("by_profile", (q) => q.eq("profileId", profileId))
      .order("desc")
      .take(25);
    const documents = await Promise.all(documentRows.map(async (d) => ({
      ...d,
      url: d.storageId ? await ctx.storage.getUrl(d.storageId) : null,
    })));
    const research = await ctx.db
      .query("research")
      .withIndex("by_profile", (q) => q.eq("profileId", profileId))
      .order("desc")
      .take(25);
    const studentCalls = await ctx.db
      .query("calls")
      .withIndex("by_profile", (q) => q.eq("profileId", profileId))
      .order("desc")
      .take(25);
    const memberships = await ctx.db
      .query("groupMembers")
      .withIndex("by_profile", (q) => q.eq("profileId", profileId))
      .take(10);
    const groups = [];
    for (const membership of memberships) {
      const group = await ctx.db.get(membership.groupId);
      if (group !== null) groups.push({ membership, group });
    }
    return {
      profile, flags: flagsWithSource, cases: casesWithCalls, paystubs, transactions,
      notifications, documents, research, studentCalls, groups,
    };
  },
});
