import { mutation, query } from "./_generated/server";
import type { MutationCtx } from "./_generated/server";
import type { Id } from "./_generated/dataModel";
import { v } from "convex/values";

// Documents Docket fills in for the student. The Filer agent (agents/filer) computes every field
// from the student file, renders the PDF, and leaves the document here in awaiting_approval.
// Nothing is ever submitted without the student's explicit approve, which can arrive from the
// dashboard, an ASI:One card or a phone call. All three land on documents:decide.
//
//   drafted ──> awaiting_approval ──> approved ──> submitted
//                        └─────────> declined

const NEXT: Record<string, string[]> = {
  drafted: ["awaiting_approval"],
  awaiting_approval: ["approved", "declined"],
  approved: ["submitted", "failed"],
  failed: ["approved", "declined"],
  declined: ["awaiting_approval"],
  submitted: [],
};

const KIND = v.union(v.literal("form_8843"), v.literal("form_843"), v.literal("form_8316"),
                     v.literal("refund_letter"), v.literal("group_request"));

const FIELD = v.object({ label: v.string(), value: v.string(), source: v.string() });

async function move(ctx: MutationCtx, documentId: Id<"documents">, to: "awaiting_approval" | "approved" |
  "declined" | "submitted" | "failed", detail: string, fields: Record<string, string> = {}) {
  const d = await ctx.db.get(documentId);
  if (d === null) throw new Error(`document ${documentId} not found`);
  if (!NEXT[d.state]?.includes(to)) throw new Error(`document is ${d.state}; it cannot move to ${to}`);
  await ctx.db.patch("documents", documentId, { state: to, ...fields });
  await ctx.db.insert("activity", {
    agent: "filer",
    action: `document_${to}`,
    detail,
    inputIds: [documentId],
    at: new Date().toISOString(),
  });
}

// One document per (profile, kind, flag). Re-filling replaces the draft as long as the student has
// not decided yet, so a re-run never asks twice and never edits something already approved.
export const draft = mutation({
  args: {
    profileId: v.id("profiles"),
    kind: KIND,
    title: v.string(),
    fields: v.array(FIELD),
    body: v.string(),
    submitTo: v.string(),
    storageId: v.optional(v.id("_storage")),
    flagId: v.optional(v.id("flags")),
    caseId: v.optional(v.id("cases")),
    groupId: v.optional(v.id("groups")),
  },
  handler: async (ctx, args) => {
    const mine = await ctx.db
      .query("documents")
      .withIndex("by_profile", (q) => q.eq("profileId", args.profileId))
      .take(50);
    const same = mine.find((d) => d.kind === args.kind && d.flagId === args.flagId && d.groupId === args.groupId);
    const now = new Date().toISOString();
    if (same) {
      if (same.state !== "drafted" && same.state !== "awaiting_approval") return same._id;
      if (same.storageId && args.storageId && same.storageId !== args.storageId) {
        await ctx.storage.delete(same.storageId);
      }
      await ctx.db.patch("documents", same._id, { ...args, state: "awaiting_approval" });
      return same._id;
    }
    const id = await ctx.db.insert("documents", { ...args, state: "drafted", createdAt: now });
    await ctx.db.insert("activity", {
      agent: "filer",
      action: "document_drafted",
      detail: `${args.title} filled in from the student file (${args.fields.length} fields)`,
      inputIds: [args.profileId],
      outputIds: [id],
      at: now,
    });
    await move(ctx, id, "awaiting_approval",
      `${args.title} is ready for ${args.submitTo}; waiting for the student to approve it`);
    return id;
  },
});

// The student's answer, from any surface. approved=false declines and nothing is sent.
export const decide = mutation({
  args: { documentId: v.id("documents"), approved: v.boolean(), via: v.optional(v.string()) },
  handler: async (ctx, { documentId, approved, via }) => {
    const d = await ctx.db.get(documentId);
    if (d === null) throw new Error(`document ${documentId} not found`);
    const how = via ? ` (${via})` : "";
    await move(ctx, documentId, approved ? "approved" : "declined",
      approved ? `Student approved ${d.title}${how}; it can now be submitted to ${d.submitTo}`
               : `Student declined ${d.title}${how}; nothing was submitted`,
      { decidedAt: new Date().toISOString() });
    return d.state;
  },
});

// Approved documents the Filer has not sent yet.
export const awaitingSubmission = query({
  args: {},
  handler: async (ctx) => {
    return await ctx.db
      .query("documents")
      .withIndex("by_state", (q) => q.eq("state", "approved"))
      .take(20);
  },
});

export const recordSubmission = mutation({
  args: { documentId: v.id("documents"), submissionRef: v.optional(v.string()), error: v.optional(v.string()) },
  handler: async (ctx, { documentId, submissionRef, error }) => {
    const d = await ctx.db.get(documentId);
    if (d === null) throw new Error(`document ${documentId} not found`);
    if (error) {
      await move(ctx, documentId, "failed", `${d.title} could not be submitted: ${error}`, { error });
      return;
    }
    await move(ctx, documentId, "submitted",
      `${d.title} submitted to ${d.submitTo}${submissionRef ? `, reference ${submissionRef}` : ""}`,
      { submittedAt: new Date().toISOString(), ...(submissionRef ? { submissionRef } : {}) });
  },
});

export const forProfile = query({
  args: { profileId: v.id("profiles") },
  handler: async (ctx, { profileId }) => {
    const rows = await ctx.db
      .query("documents")
      .withIndex("by_profile", (q) => q.eq("profileId", profileId))
      .order("desc")
      .take(50);
    return await Promise.all(rows.map(async (d) => ({
      ...d,
      url: d.storageId ? await ctx.storage.getUrl(d.storageId) : null,
    })));
  },
});

export const get = query({
  args: { documentId: v.id("documents") },
  handler: async (ctx, { documentId }) => {
    const d = await ctx.db.get(documentId);
    if (d === null) return null;
    return { ...d, url: d.storageId ? await ctx.storage.getUrl(d.storageId) : null };
  },
});

// What a phone call or a chat should offer next: the oldest document still waiting on the student.
export const nextAwaitingApproval = query({
  args: { profileId: v.id("profiles") },
  handler: async (ctx, { profileId }) => {
    const rows = await ctx.db
      .query("documents")
      .withIndex("by_profile", (q) => q.eq("profileId", profileId))
      .take(50);
    return rows.filter((d) => d.state === "awaiting_approval")
      .sort((a, b) => a.createdAt.localeCompare(b.createdAt))[0] ?? null;
  },
});
