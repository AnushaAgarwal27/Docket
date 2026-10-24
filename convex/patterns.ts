import { query } from "./_generated/server";

// Employer pattern: when several students at one employer get the same withholding flag, it is likely a
// payroll setup problem rather than a one-off. Counts come from flags the rules engine wrote; the cohort
// beyond the demo student is simulated (profiles.simulated) and the dashboard labels it so.
const PATTERN_MIN = 3;

export const byEmployer = query({
  args: {},
  handler: async (ctx) => {
    const profiles = await ctx.db.query("profiles").take(50);
    const rows = new Map<string, { employer: string; students: number; flagged: number; withheldCents: number; simulated: number }>();
    for (const p of profiles) {
      const stubs = await ctx.db.query("paystubs").withIndex("by_profile", (q) => q.eq("profileId", p._id)).take(100);
      if (stubs.length === 0) continue;
      const flags = await ctx.db.query("flags").withIndex("by_profile", (q) => q.eq("profileId", p._id)).take(50);
      const fica = flags.find((f) => f.ruleId === "FICA_EXEMPT_F1");
      for (const employer of new Set(stubs.map((s) => s.employer))) {
        const row = rows.get(employer) ?? { employer, students: 0, flagged: 0, withheldCents: 0, simulated: 0 };
        row.students += 1;
        if (p.simulated) row.simulated += 1;
        if (fica) {
          row.flagged += 1;
          row.withheldCents += fica.amountCents;
        }
        rows.set(employer, row);
      }
    }
    const employers = [...rows.values()]
      .map((r) => ({ ...r, pattern: r.flagged >= PATTERN_MIN }))
      .sort((a, b) => b.flagged - a.flagged || b.students - a.students);
    return { employers, minForPattern: PATTERN_MIN, anySimulated: employers.some((r) => r.simulated > 0) };
  },
});
