import { internalMutation, internalQuery, mutation, query } from "./_generated/server";
import type { MutationCtx, QueryCtx } from "./_generated/server";
import type { Doc, Id } from "./_generated/dataModel";
import { api } from "./_generated/api";
import { v } from "convex/values";

// What the Cartesia student line is allowed to know and do, served to it over convex/http.ts.
//
// Everything the voice agent says about the student comes from here, assembled in code. The voice
// model is never handed the student file and never computes a number; it reads sentences back.
// Each tool returns plain text because Cartesia passes a tool result straight to the voice model.
//
// The privacy rule for this file: these endpoints answer for exactly one profile, identified by the
// number that called in or by the profile_id we put on an outbound call. They never list students,
// never name another student, and never read out bank rows or identifiers.

/** Money as a voice agent should say it. */
const spoken = (cents: number) => {
  const dollars = Math.floor(Math.abs(cents) / 100);
  const rest = Math.abs(cents) % 100;
  const d = `${dollars.toLocaleString("en-US")} dollar${dollars === 1 ? "" : "s"}`;
  return rest === 0 ? d : `${d} and ${rest} cent${rest === 1 ? "" : "s"}`;
};

const CASE_STATE: Record<string, string> = {
  open: "just opened",
  awaiting_approval: "waiting for your go-ahead",
  contacting_employer: "with payroll now",
  written_request: "in writing with payroll",
  awaiting_response: "waiting on payroll's answer",
  refund_received: "paid",
  escalate_irs: "going to the I.R.S. instead, because payroll refused",
  closed: "closed",
};

// ---------- who is on the line ----------

/** The caller, by the number they rang from. Returns null when we do not know the number. */
export const identify = internalQuery({
  args: { fromNumber: v.string() },
  handler: async (ctx, { fromNumber }) => {
    const digits = fromNumber.replace(/\D/g, "").slice(-10);
    if (digits.length < 10) return null;
    const profiles = await ctx.db.query("profiles").take(50);
    const match = profiles.find((p) => !p.simulated && (p.phone ?? "").replace(/\D/g, "").slice(-10) === digits);
    return match === undefined ? null : { profileId: match._id, name: match.name, firstName: match.name.split(" ")[0] };
  },
});

// ---------- what is going on with this student ----------

async function brief(ctx: QueryCtx, profileId: Id<"profiles">): Promise<string> {
  const profile = await ctx.db.get(profileId);
  if (profile === null) return "I could not find your file. Please try again later.";
  const first = profile.name.split(" ")[0];
  const flags = await ctx.db.query("flags").withIndex("by_profile", (q) => q.eq("profileId", profileId)).take(25);
  const cases = await ctx.db.query("cases").withIndex("by_profile", (q) => q.eq("profileId", profileId)).take(25);
  const docs = await ctx.db.query("documents").withIndex("by_profile", (q) => q.eq("profileId", profileId)).take(25);
  const memberships = await ctx.db
    .query("groupMembers").withIndex("by_profile", (q) => q.eq("profileId", profileId)).take(10);

  const lines: string[] = [];
  const open = flags.filter((f) => f.status !== "resolved");
  const money = open.reduce((s, f) => s + f.amountCents, 0);
  if (open.length === 0) lines.push(`${first}, there is nothing open on your file right now.`);
  else {
    lines.push(
      `${first}, you have ${open.length} open item${open.length === 1 ? "" : "s"}` +
      (money > 0 ? `, worth ${spoken(money)} in total.` : "."),
    );
  }
  for (const c of cases.filter((c) => c.state !== "closed")) {
    lines.push(`Your refund case for ${spoken(c.amountCents)} is ${CASE_STATE[c.state] ?? c.state.replace(/_/g, " ")}.`);
  }
  const waiting = docs.filter((d) => d.state === "awaiting_approval");
  for (const d of waiting) {
    lines.push(`I have filled in your ${d.title}. It is ready for ${d.submitTo}, and I need your yes before I send it.`);
  }
  const invited = memberships.filter((m) => m.state === "invited");
  for (const m of invited) {
    const group = await ctx.db.get(m.groupId);
    if (group === null) continue;
    const members = await ctx.db
      .query("groupMembers").withIndex("by_group", (q) => q.eq("groupId", group._id)).take(200);
    lines.push(
      `${members.length} students at ${group.employer} have the same problem you do. ` +
      `They are asking together, and you can join. Joining does not change your own case.`,
    );
  }
  const refunded = cases.filter((c) => c.outcome === "refunded");
  for (const c of refunded.slice(0, 1)) lines.push(`Your ${spoken(c.amountCents)} refund has already landed.`);
  return lines.join(" ");
}

export const studentBrief = internalQuery({
  args: { profileId: v.string() },
  handler: async (ctx, { profileId }) => {
    const id = ctx.db.normalizeId("profiles", profileId);
    if (id === null) return null;
    return { profileId: id, text: await brief(ctx, id) };
  },
});

// ---------- answering a question on the call ----------

/** Research we already hold that matches what was asked. Keyword overlap is deliberately dumb:
 *  a weak match should fall through to real research rather than be stretched to fit. */
export const storedAnswer = internalQuery({
  args: { profileId: v.string(), question: v.string() },
  handler: async (ctx, { profileId, question }) => {
    const id = ctx.db.normalizeId("profiles", profileId);
    if (id === null) return null;
    const words = new Set(
      question.toLowerCase().split(/[^a-z0-9]+/).filter((w) => w.length > 3),
    );
    if (words.size === 0) return null;
    const mine = await ctx.db.query("research").withIndex("by_profile", (q) => q.eq("profileId", id)).order("desc").take(25);
    const shared = (await ctx.db.query("research").withIndex("by_kind", (q) => q.eq("kind", "watch")).order("desc").take(25))
      .filter((r) => r.profileId === undefined);
    let best: { row: Doc<"research">; score: number } | null = null;
    for (const row of [...mine, ...shared]) {
      const hay = `${row.topic} ${row.question ?? ""} ${row.answer}`.toLowerCase();
      let score = 0;
      for (const w of words) if (hay.includes(w)) score += 1;
      if (best === null || score > best.score) best = { row, score };
    }
    // Needs most of the question's content words, not just one, before it counts as an answer.
    if (best === null || best.score < Math.max(2, Math.ceil(words.size * 0.6))) return null;
    return { answer: best.row.answer, topic: best.row.topic, confidence: best.row.confidence };
  },
});

/** Nothing on file answered it, so record the question for the research agent. */
export const askResearch = internalMutation({
  args: {
    profileId: v.string(),
    question: v.string(),
    askedVia: v.union(v.literal("voice"), v.literal("chat"), v.literal("dashboard")),
  },
  handler: async (ctx, { profileId, question, askedVia }) => {
    const id = ctx.db.normalizeId("profiles", profileId);
    if (id === null) return null;
    const now = new Date().toISOString();
    const requestId = await ctx.db.insert("researchRequests", {
      profileId: id, question, askedVia, state: "pending", createdAt: now,
    });
    await ctx.db.insert("activity", {
      agent: "voice",
      action: "question_taken",
      detail: `Question asked by ${askedVia}: ${question.slice(0, 160)}`,
      inputIds: [id],
      outputIds: [requestId],
      at: now,
    });
    return requestId;
  },
});

export const pendingResearch = query({
  args: { limit: v.optional(v.number()) },
  handler: async (ctx, { limit }) => {
    return await ctx.db
      .query("researchRequests")
      .withIndex("by_state", (q) => q.eq("state", "pending"))
      .take(limit ?? 10);
  },
});

export const resolveResearch = mutation({
  args: {
    requestId: v.id("researchRequests"),
    researchId: v.optional(v.id("research")),
    error: v.optional(v.string()),
  },
  handler: async (ctx, { requestId, researchId, error }) => {
    await ctx.db.patch("researchRequests", requestId, {
      state: error ? "failed" : "answered",
      answeredAt: new Date().toISOString(),
      ...(researchId ? { researchId } : {}),
      ...(error ? { error } : {}),
    });
  },
});

// ---------- the student deciding something on the phone ----------

async function profileOf(ctx: MutationCtx, profileId: string) {
  const id = ctx.db.normalizeId("profiles", profileId);
  return id === null ? null : id;
}

/** A yes or no said out loud, applied to whatever is actually waiting. Returns what it did, in
 *  words the agent can read back. The subject is chosen in code from the file, never by the model,
 *  so "yes" can only ever approve the thing we just described. */
export const decide = internalMutation({
  args: {
    profileId: v.string(),
    subject: v.union(v.literal("refund"), v.literal("document"), v.literal("group")),
    yes: v.boolean(),
  },
  handler: async (ctx, { profileId, subject, yes }) => {
    const id = await profileOf(ctx, profileId);
    if (id === null) return "I could not find your file, so I have not changed anything.";
    const now = new Date().toISOString();

    if (subject === "refund") {
      const cases = await ctx.db.query("cases").withIndex("by_profile", (q) => q.eq("profileId", id)).take(25);
      const waiting = cases.find((c) => c.state === "awaiting_approval");
      if (waiting === undefined) return "There is nothing waiting for your approval right now.";
      if (!yes) {
        await ctx.runMutation(api.cases.decline, { caseId: waiting._id });
        return "Understood. I will not contact payroll. The issue stays on your file.";
      }
      await ctx.runMutation(api.cases.approve, { caseId: waiting._id });
      return `Thank you. I will contact payroll about your ${spoken(waiting.amountCents)} refund and tell you what they say.`;
    }

    if (subject === "document") {
      const docs = await ctx.db.query("documents").withIndex("by_profile", (q) => q.eq("profileId", id)).take(25);
      const waiting = docs.filter((d) => d.state === "awaiting_approval")
        .sort((a, b) => a.createdAt.localeCompare(b.createdAt))[0];
      if (waiting === undefined) return "There is no document waiting for your approval.";
      await ctx.db.patch("documents", waiting._id, {
        state: yes ? "approved" : "declined", decidedAt: now,
      });
      await ctx.db.insert("activity", {
        agent: "filer",
        action: yes ? "document_approved" : "document_declined",
        detail: `Student ${yes ? "approved" : "declined"} ${waiting.title} on the phone`,
        inputIds: [waiting._id],
        at: now,
      });
      return yes
        ? `Thank you. I will send your ${waiting.title} to ${waiting.submitTo} and text you the confirmation.`
        : `Understood. I will not send your ${waiting.title}. It stays on your file if you change your mind.`;
    }

    const memberships = await ctx.db
      .query("groupMembers").withIndex("by_profile", (q) => q.eq("profileId", id)).take(10);
    const invited = memberships.filter((m) => m.state === "invited")
      .sort((a, b) => a.invitedAt.localeCompare(b.invitedAt))[0];
    if (invited === undefined) return "There is no group case waiting for your answer.";
    await ctx.runMutation(api.groups.respond, {
      groupId: invited.groupId, profileId: id, join: yes, via: "phone",
    });
    const group = await ctx.db.get(invited.groupId);
    return yes
      ? `You are in. I will add you to the request to ${group?.employer ?? "the employer"} and keep your own case going as well.`
      : "Understood, I will leave you out of the group. Your own case is not affected.";
  },
});

export const logCall = internalMutation({
  args: {
    profileId: v.string(),
    direction: v.union(v.literal("outbound"), v.literal("inbound")),
    purpose: v.string(),
    summary: v.string(),
    notificationId: v.optional(v.string()),
  },
  handler: async (ctx, { profileId, direction, purpose, summary, notificationId }) => {
    const id = await profileOf(ctx, profileId);
    if (id === null) return null;
    const now = new Date().toISOString();
    const callId = await ctx.db.insert("calls", {
      profileId: id, direction, purpose, summary, answeredBy: "The student", at: now,
    });
    await ctx.db.insert("activity", {
      agent: "voice",
      action: direction === "inbound" ? "student_called_in" : "student_call_finished",
      detail: `${purpose.replace(/_/g, " ")}: ${summary}`,
      inputIds: [id],
      outputIds: [callId],
      at: now,
    });
    // A call that was placed to deliver a message counts as that message being delivered.
    const nid = notificationId ? ctx.db.normalizeId("notifications", notificationId) : null;
    if (nid !== null) {
      const note = await ctx.db.get(nid);
      if (note !== null && note.state !== "acknowledged") {
        await ctx.db.patch("notifications", nid, { state: "delivered" });
      }
    }
    return callId;
  },
});
