import { mutation } from "./_generated/server";

// Stand-in seed until the Nessie + paystub PDF pipeline lands. Synthetic data only.
// Sources are kept: they are fetched official text, not demo state.
const DEMO_TABLES = ["calls", "cases", "flags", "paystubs", "transactions", "activity", "profiles"] as const;

export const resetDemo = mutation({
  args: {},
  handler: async (ctx) => {
    for (const table of DEMO_TABLES) {
      for await (const row of ctx.db.query(table)) {
        await ctx.db.delete(table, row._id);
      }
    }

    const profileId = await ctx.db.insert("profiles", {
      name: "Priya Sharma",
      visa: "F-1",
      arrivalDate: "2024-08-15",
      school: "UC Berkeley",
      homeCountry: "India",
      homeCurrency: "INR",
      workAuth: "on-campus",
      phoneMasked: "***-***-0142",
      // Filed for 2025, so the demo produces exactly two flags (see docs/PLAN_NOTES.md).
      filed8843Years: [2025],
    });

    // 8 biweekly Spring 2026 paystubs, 40 hours at $18. Paystub 5 splits 16 + 24.
    const firstStart = Date.UTC(2026, 0, 12);
    const day = 24 * 60 * 60 * 1000;
    for (let i = 0; i < 8; i++) {
      const start = new Date(firstStart + i * 14 * day);
      const end = new Date(firstStart + (i * 14 + 13) * day);
      await ctx.db.insert("paystubs", {
        profileId,
        periodStart: start.toISOString().slice(0, 10),
        periodEnd: end.toISOString().slice(0, 10),
        employer: "University Dining Services",
        grossCents: 72000,
        hoursByWeek: i === 4 ? [16, 24] : [20, 20],
        ssCents: 4464,
        medicareCents: 1044,
        netCents: 66492,
        sourceFile: `seed:paystub_${String(i + 1).padStart(2, "0")}`,
      });
    }

    await ctx.db.insert("activity", {
      agent: "seed",
      action: "reset_demo",
      detail: "Wiped demo tables; seeded Priya Sharma with 8 Spring 2026 paystubs",
      outputIds: [profileId],
      at: new Date().toISOString(),
    });
    return profileId;
  },
});
