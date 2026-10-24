import { mutation, query } from "./_generated/server";
import type { QueryCtx } from "./_generated/server";
import type { Doc } from "./_generated/dataModel";
import { v } from "convex/values";
import schema from "./schema";

// The receipt behind each finding: paystub PDFs (Ledger) and the drafted letter (Caseworker), in Convex file storage.

// Step 1 of an upload: a short-lived URL the agent POSTs the file bytes to; the response holds the storageId.
export const generateUploadUrl = mutation({
  args: {},
  handler: async (ctx) => {
    return await ctx.storage.generateUploadUrl();
  },
});

// Step 2: link the stored file to its paystub or flag. Re-attaching the same kind for the same
// paystub or flag replaces the old file, so re-runs never pile up duplicates.
export const attach = mutation({
  args: schema.tables.files.validator.omit("createdAt").fields,
  handler: async (ctx, args) => {
    const linked = args.flagId
      ? await ctx.db.query("files").withIndex("by_flag", (q) => q.eq("flagId", args.flagId)).take(20)
      : args.paystubId
        ? await ctx.db.query("files").withIndex("by_paystub", (q) => q.eq("paystubId", args.paystubId)).take(20)
        : [];
    for (const old of linked.filter((f) => f.kind === args.kind)) {
      await ctx.storage.delete(old.storageId);
      await ctx.db.delete("files", old._id);
    }
    return await ctx.db.insert("files", { ...args, createdAt: new Date().toISOString() });
  },
});

async function withUrl(ctx: QueryCtx, file: Doc<"files">) {
  return { ...file, url: await ctx.storage.getUrl(file.storageId) };
}

// Everything behind one flag: its own files (the letter) plus the PDFs of the paystubs the rule hit on.
export const forFlag = query({
  args: { flagId: v.id("flags") },
  handler: async (ctx, { flagId }) => {
    const flag = await ctx.db.get(flagId);
    if (flag === null) return null;
    const own = await ctx.db.query("files").withIndex("by_flag", (q) => q.eq("flagId", flagId)).take(20);
    const paystubFiles = [];
    for (const paystubId of flag.paystubIds ?? []) {
      const paystub = await ctx.db.get(paystubId);
      const files = await ctx.db.query("files").withIndex("by_paystub", (q) => q.eq("paystubId", paystubId)).take(5);
      for (const f of files) {
        paystubFiles.push({ ...(await withUrl(ctx, f)), periodStart: paystub?.periodStart ?? null });
      }
    }
    paystubFiles.sort((a, b) => (a.periodStart ?? "").localeCompare(b.periodStart ?? ""));
    return {
      letters: await Promise.all(own.filter((f) => f.kind === "letter").map((f) => withUrl(ctx, f))),
      forms: await Promise.all(own.filter((f) => f.kind === "form").map((f) => withUrl(ctx, f))),
      paystubs: paystubFiles,
    };
  },
});
