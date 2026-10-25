import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

// The shared student file. Every agent reads and writes here; agents never call each other.
// Money is integer cents everywhere. No floats, no model-written numbers.
// Fields marked "added" are not in the build plan's starter schema; see docs/PLAN_NOTES.md.
export default defineSchema({
  profiles: defineTable({
    name: v.string(), visa: v.string(), arrivalDate: v.string(),
    school: v.string(), homeCountry: v.string(), homeCurrency: v.string(),
    workAuth: v.string(), phoneMasked: v.string(),
    filed8843Years: v.optional(v.array(v.number())), // added: needs_8843 needs a filing record
    employer: v.optional(v.string()), // added: the student's on-campus employer
    filings: v.optional(v.array(v.object({ year: v.number(), form: v.string() }))), // added: forms filed per tax year
    // added for the Hearing's objection checks; missing values mean "ask", never "assume"
    employmentType: v.optional(v.union(v.literal("employee"), v.literal("contractor"))),
    employerIsSchool: v.optional(v.boolean()),
    enrolled: v.optional(v.boolean()),
    simulated: v.optional(v.boolean()), // added: synthetic cohort for the employer pattern view, never the demo student
    // added: how Docket reaches the student. phone is E.164 and is the number Cartesia dials and texts;
    // nothing is dialled or texted without the matching consent flag, which the student sets themselves.
    phone: v.optional(v.string()),
    voiceConsent: v.optional(v.boolean()),
    smsConsent: v.optional(v.boolean()),
    // added: the student's standing answer on joining group cases ("ask" means ask every time)
    groupPreference: v.optional(v.union(v.literal("ask"), v.literal("always"), v.literal("never"))),
  }).index("by_phone", ["phone"]),
  transactions: defineTable({
    profileId: v.id("profiles"), kind: v.string(), amountCents: v.number(),
    date: v.string(), counterparty: v.string(), memo: v.string(), nessieId: v.string(),
  }).index("by_profile", ["profileId"]).index("by_nessie", ["nessieId"]), // added: dedupe on re-poll
  paystubs: defineTable({
    profileId: v.id("profiles"), periodStart: v.string(), periodEnd: v.string(),
    employer: v.string(), grossCents: v.number(), hoursByWeek: v.array(v.number()),
    ssCents: v.number(), medicareCents: v.number(), netCents: v.number(), sourceFile: v.string(),
    depositId: v.optional(v.id("transactions")), // added: "each paystub links to its deposit"
    warnings: v.optional(v.array(v.string())), // added: low-confidence code-check results
  }).index("by_profile", ["profileId"]),
  sources: defineTable({
    url: v.string(), title: v.string(), text: v.string(), fetchedAt: v.string(), hash: v.string(),
  }).index("by_url", ["url"]),
  flags: defineTable({
    profileId: v.id("profiles"), ruleId: v.string(), amountCents: v.number(),
    explanation: v.string(), quote: v.string(), sourceId: v.id("sources"), status: v.string(),
    paystubIds: v.optional(v.array(v.id("paystubs"))), // added: the paystubs the rule hit on, for the receipt
    ssCents: v.optional(v.number()), // added: the rule's own Social Security and Medicare totals,
    medicareCents: v.optional(v.number()), // so letters never re-add paystubs
  }).index("by_profile", ["profileId"]),
  cases: defineTable({
    flagId: v.id("flags"), state: v.string(), amountCents: v.number(),
    nextFollowUp: v.string(), outcome: v.optional(v.string()),
    profileId: v.optional(v.id("profiles")), // added: Ledger refund matching looks up open cases per student
    deadline: v.optional(v.string()), // added: plan lists "deadlines" for cases
    draft: v.optional(v.string()), // added: request text Priya approves before any call
    callRequestedAt: v.optional(v.string()), // added: set once when the Caseworker claims the payroll call
    callRequestId: v.optional(v.string()), // added: Cartesia agent_call_id for that call
    callError: v.optional(v.string()), // added: why the call could not start, if it failed
    callAttempts: v.optional(v.number()), // added: payroll calls placed so far (1 = first call)
    payrollScript: v.optional(v.union(v.literal("cooperate"), v.literal("stall_once"), v.literal("refuse_once"))), // added: rehearsal setting
    writtenRequest: v.optional(v.string()), // added: letter the Caseworker prepares after a stall or refusal
    writtenRequestAt: v.optional(v.string()),
  }).index("by_state", ["state"]).index("by_flag", ["flagId"]).index("by_profile", ["profileId"]),
  // Every call Docket is part of. A payroll call carries caseId; a call with the student carries
  // profileId and no case. direction says who dialled: "outbound" is Docket calling, "inbound" is
  // the student calling Docket's line.
  calls: defineTable({
    caseId: v.optional(v.id("cases")), answeredBy: v.string(), at: v.string(), summary: v.string(),
    promisedBy: v.optional(v.string()), referenceNo: v.optional(v.string()),
    transcriptUrl: v.optional(v.string()), // added: plan lists "transcript link"
    profileId: v.optional(v.id("profiles")), // added: calls with the student, which have no case
    direction: v.optional(v.union(v.literal("outbound"), v.literal("inbound"))),
    purpose: v.optional(v.string()), // added: payroll_refund | student_alert | student_inbound | group_request
    toNumber: v.optional(v.string()), // added: what was actually dialled, so the demo redirect is visible
    callRequestId: v.optional(v.string()),
  }).index("by_case", ["caseId"]).index("by_profile", ["profileId"]),

  // ---- The message layer: one row per thing Docket told the student, whatever the channel ----
  // Written by any agent through notifications:queue, then delivered by the Coordinator (chat),
  // the voice agent (a phone call) or the SMS sender. The dashboard renders the same rows as a thread.
  notifications: defineTable({
    profileId: v.id("profiles"),
    channel: v.union(v.literal("chat"), v.literal("voice"), v.literal("sms"), v.literal("inapp")),
    kind: v.string(), // finding | case_update | document_ready | group_invite | research | refund
    title: v.string(),
    body: v.string(), // already rendered for this channel and already checked by agents/guard.py
    state: v.union(v.literal("queued"), v.literal("sent"), v.literal("delivered"),
                   v.literal("acknowledged"), v.literal("failed")),
    at: v.string(),
    sentAt: v.optional(v.string()),
    ackedAt: v.optional(v.string()),
    error: v.optional(v.string()),
    refs: v.optional(v.array(v.string())), // the case, flag, document or group this is about
    // set when this notification expects an answer, so a voice call or a tap can resolve it
    awaiting: v.optional(v.union(v.literal("approval"), v.literal("group_optin"), v.literal("none"))),
    answer: v.optional(v.string()),
  }).index("by_profile", ["profileId"]).index("by_state", ["state"])
    .index("by_profile_and_channel", ["profileId", "channel"]),

  // ---- Athena: what the research agent found, and where it found it ----
  research: defineTable({
    profileId: v.optional(v.id("profiles")), // absent for findings that apply to everyone
    kind: v.union(v.literal("watch"), v.literal("ask")),
    topic: v.string(),
    question: v.optional(v.string()), // the student's words, when this came from a call or chat
    answer: v.string(), // the synthesis, already checked by agents/guard.py
    sources: v.array(v.object({
      title: v.string(), url: v.string(),
      publishedAt: v.optional(v.string()), excerpt: v.optional(v.string()),
    })),
    engine: v.string(), // asi1-agentic | asi1-extended-agentic | claude
    confidence: v.union(v.literal("high"), v.literal("medium"), v.literal("low")),
    actionable: v.boolean(), // true when it changes what the student should do, so it is worth a text
    createdAt: v.string(),
    notifiedAt: v.optional(v.string()),
  }).index("by_profile", ["profileId"]).index("by_kind", ["kind"]),

  // A question the student asked that could not be answered from the file on the spot. The voice
  // tool records it and promises an answer; the research agent picks it up, researches it properly
  // and sends the answer back as a message. Nothing is guessed at on the call to fill the gap.
  researchRequests: defineTable({
    profileId: v.id("profiles"),
    question: v.string(),
    askedVia: v.union(v.literal("voice"), v.literal("chat"), v.literal("dashboard")),
    state: v.union(v.literal("pending"), v.literal("answered"), v.literal("failed")),
    researchId: v.optional(v.id("research")),
    error: v.optional(v.string()),
    createdAt: v.string(),
    answeredAt: v.optional(v.string()),
  }).index("by_state", ["state"]).index("by_profile", ["profileId"]),

  // ---- Documents Docket fills in for the student, which only the student can submit ----
  documents: defineTable({
    profileId: v.id("profiles"),
    kind: v.union(v.literal("form_8843"), v.literal("form_843"), v.literal("form_8316"),
                  v.literal("refund_letter"), v.literal("group_request")),
    title: v.string(),
    // Every field is filled in code from the student file. `source` says which stored value it came from,
    // so the student (and a judge) can see nothing here was written by a model.
    fields: v.array(v.object({ label: v.string(), value: v.string(), source: v.string() })),
    body: v.string(), // the rendered text, shown for review before anything is submitted
    storageId: v.optional(v.id("_storage")), // the PDF
    state: v.union(v.literal("drafted"), v.literal("awaiting_approval"), v.literal("approved"),
                   v.literal("declined"), v.literal("submitted"), v.literal("failed")),
    submitTo: v.string(), // "IRS", "University Dining Services payroll", ...
    flagId: v.optional(v.id("flags")),
    caseId: v.optional(v.id("cases")),
    groupId: v.optional(v.id("groups")),
    createdAt: v.string(),
    decidedAt: v.optional(v.string()),
    submittedAt: v.optional(v.string()),
    submissionRef: v.optional(v.string()),
    error: v.optional(v.string()),
  }).index("by_profile", ["profileId"]).index("by_state", ["state"]).index("by_flag", ["flagId"]),

  // ---- Group cases: one employer, one rule, many students with the same problem ----
  groups: defineTable({
    employer: v.string(),
    ruleId: v.string(),
    state: v.union(v.literal("forming"), v.literal("open"), v.literal("contacting"), v.literal("closed")),
    threshold: v.number(), // how many flagged students it took to open this group
    summary: v.string(),
    createdAt: v.string(),
    openedAt: v.optional(v.string()),
    // the combined ask, recomputed from joined members only; never includes a student who did not join
    joinedCount: v.number(),
    joinedCents: v.number(),
    contactId: v.optional(v.id("contacts")),
    caseNote: v.optional(v.string()), // what the researcher found about similar public filings
  }).index("by_employer_and_rule", ["employer", "ruleId"]).index("by_state", ["state"]),

  groupMembers: defineTable({
    groupId: v.id("groups"),
    profileId: v.id("profiles"),
    flagId: v.id("flags"),
    amountCents: v.number(),
    state: v.union(v.literal("invited"), v.literal("joined"), v.literal("declined")),
    invitedAt: v.string(),
    decidedAt: v.optional(v.string()),
  }).index("by_group", ["groupId"]).index("by_profile", ["profileId"])
    .index("by_group_and_profile", ["groupId", "profileId"]),

  // ---- Who to call. Seeded for the demo, extended by the research agent. ----
  contacts: defineTable({
    name: v.string(),
    org: v.string(),
    role: v.union(v.literal("payroll"), v.literal("irs"), v.literal("school"),
                  v.literal("legal_aid"), v.literal("attorney")),
    phone: v.string(), // E.164. In demo mode every call is redirected to DEMO_CALL_NUMBER anyway.
    email: v.optional(v.string()),
    url: v.optional(v.string()),
    foundBy: v.union(v.literal("seed"), v.literal("research")),
    verified: v.boolean(), // true only when the number came from an official page the code fetched
    note: v.optional(v.string()),
    createdAt: v.string(),
  }).index("by_role", ["role"]),
  // Stored documents behind each finding: the paystub PDFs and the drafted letter (Convex file storage).
  files: defineTable({
    storageId: v.id("_storage"),
    kind: v.union(v.literal("paystub"), v.literal("letter"), v.literal("form")),
    filename: v.string(),
    paystubId: v.optional(v.id("paystubs")),
    flagId: v.optional(v.id("flags")),
    createdAt: v.string(),
  }).index("by_flag", ["flagId"]).index("by_paystub", ["paystubId"]),
  activity: defineTable({
    agent: v.string(), action: v.string(), detail: v.string(),
    sourceId: v.optional(v.id("sources")), at: v.string(),
    inputIds: v.optional(v.array(v.string())), // added: plan lists input and output ids
    outputIds: v.optional(v.array(v.string())),
    // added: agent-to-agent messages are logged too (kind "message"), with who sent what to whom
    kind: v.optional(v.string()),
    sender: v.optional(v.string()),
    receiver: v.optional(v.string()),
    summary: v.optional(v.string()),
  }),
  // The Hearing: Tax (advocate) and Auditor argue a flag before it reaches the student; the verdict is decided in code.
  hearings: defineTable({
    profileId: v.id("profiles"),
    ruleId: v.string(),
    flagId: v.optional(v.id("flags")), // absent when the rule did not fire and the Auditor defeated the claim
    caseId: v.optional(v.id("cases")),
    rounds: v.array(v.object({
      round: v.number(),
      side: v.union(v.literal("advocate"), v.literal("auditor")),
      objectionId: v.optional(v.string()),
      argument: v.string(),
      evidenceIds: v.array(v.string()),
      at: v.string(),
    })),
    verdict: v.union(v.literal("upheld"), v.literal("downgraded"), v.literal("needs_human"), v.literal("defeated")),
    reason: v.string(),
    createdAt: v.string(),
  }).index("by_flag", ["flagId"]).index("by_profile", ["profileId"]),
});
