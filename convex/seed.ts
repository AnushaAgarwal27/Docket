import { mutation } from "./_generated/server";
import schema from "./schema";

// Wipes demo state and re-creates the student. Synthetic data only.
// Paystubs are not seeded here: the Ledger reads them from the PDFs in seed/paystubs/.
// Sources are kept: they are fetched official text, not demo state.
const DEMO_TABLES = ["calls", "cases", "flags", "paystubs", "transactions", "activity", "profiles"] as const;

export const resetDemo = mutation({
  // The profile comes from seed/demo_data.py, the single source of truth for Priya.
  args: { profile: schema.tables.profiles.validator },
  handler: async (ctx, { profile }) => {
    for (const table of DEMO_TABLES) {
      for await (const row of ctx.db.query(table)) {
        await ctx.db.delete(table, row._id);
      }
    }
    const profileId = await ctx.db.insert("profiles", profile);
    await ctx.db.insert("activity", {
      agent: "seed",
      action: "reset_demo",
      detail: `Wiped demo tables; seeded ${profile.name}. The Ledger records paystubs from the PDFs.`,
      outputIds: [profileId],
      at: new Date().toISOString(),
    });
    return profileId;
  },
});
