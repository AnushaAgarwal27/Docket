import { internalQuery } from "./_generated/server";
import { v } from "convex/values";

// What the Cartesia voice agent is told about a case when it calls get_case_summary.
// Every number here is computed in code from the student file; the voice model only reads it out.
// It deliberately leaves out everything payroll does not need (hours flags, visa history, bank data).

const usd = (cents: number) =>
  "$" + (cents / 100).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const longDate = (iso: string) =>
  new Date(iso + "T12:00:00Z").toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric", timeZone: "UTC" });

export const caseSummary = internalQuery({
  args: { caseId: v.string() },
  handler: async (ctx, { caseId }) => {
    const id = ctx.db.normalizeId("cases", caseId);
    if (id === null) return null;
    const c = await ctx.db.get(id);
    if (c === null || c.profileId === undefined) return null;
    const profile = await ctx.db.get(c.profileId);
    const flag = await ctx.db.get(c.flagId);
    if (profile === null || flag === null) return null;
    const source = await ctx.db.get(flag.sourceId);
    const stubs = await ctx.db
      .query("paystubs")
      .withIndex("by_profile", (q) => q.eq("profileId", profile._id))
      .take(100);
    if (stubs.length === 0) return null;
    const ss = stubs.reduce((s, p) => s + p.ssCents, 0);
    const medicare = stubs.reduce((s, p) => s + p.medicareCents, 0);
    const first = stubs.map((p) => p.periodStart).sort()[0];
    const last = stubs.map((p) => p.periodEnd).sort().at(-1)!;
    const year = Number(last.slice(0, 4)) - Number(profile.arrivalDate.slice(0, 4)) + 1;
    const followUp = (c.callAttempts ?? 1) >= 2 && c.writtenRequestAt !== undefined;
    const text = [
      `Case ${c._id}. Current state: ${c.state.replace(/_/g, " ")}.`,
      followUp ? `This is a follow-up call. A written request was prepared on ${longDate(c.writtenRequestAt!.slice(0, 10))} after the first call.` : "",
      `You are asking ${stubs[0].employer} payroll to refund ${usd(c.amountCents)} to ${profile.name}.`,
      `Social Security of ${usd(ss)} and Medicare of ${usd(medicare)} were withheld across ${stubs.length} paychecks, for pay periods from ${longDate(first)} to ${longDate(last)}.`,
      `${profile.name} is a nonresident alien student in ${profile.visa} status, in calendar year ${year} of 5 in the United States.`,
      source ? `${source.title} says: "${flag.quote}"` : `The rule: "${flag.quote}"`,
      `Ask for two things: refund ${usd(c.amountCents)}, and stop withholding Social Security and Medicare from future paychecks.`,
      `Then ask for the date the refund will be issued and a reference number.`,
      `Do not discuss anything else about ${profile.name}. If payroll needs more information or needs to speak with her directly, record the outcome as needs_student.`,
    ].filter(Boolean).join(" ");
    return { caseId: c._id, state: c.state, text };
  },
});
