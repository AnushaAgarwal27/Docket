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
    simulated: v.optional(v.boolean()), // added: synthetic cohort for the employer pattern view, never the demo student
  }),
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
  calls: defineTable({
    caseId: v.id("cases"), answeredBy: v.string(), at: v.string(), summary: v.string(),
    promisedBy: v.optional(v.string()), referenceNo: v.optional(v.string()),
    transcriptUrl: v.optional(v.string()), // added: plan lists "transcript link"
  }).index("by_case", ["caseId"]),
  activity: defineTable({
    agent: v.string(), action: v.string(), detail: v.string(),
    sourceId: v.optional(v.id("sources")), at: v.string(),
    inputIds: v.optional(v.array(v.string())), // added: plan lists input and output ids
    outputIds: v.optional(v.array(v.string())),
  }),
});
