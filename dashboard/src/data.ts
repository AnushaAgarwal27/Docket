import type { FunctionReturnType } from "convex/server";
import type { api } from "../../convex/_generated/api";
import type { Doc, Id, TableNames } from "../../convex/_generated/dataModel";

// Everything the dashboard renders comes from one Snapshot plus the activity feed,
// whether it is live from Convex or the labelled demo copy below.
export type Snapshot = NonNullable<FunctionReturnType<typeof api.dashboard.snapshot>>;
export type Flag = Snapshot["flags"][number];
export type Case = Snapshot["cases"][number];
export type Paystub = Snapshot["paystubs"][number];
export type Activity = Doc<"activity">;
export type Timeline = NonNullable<FunctionReturnType<typeof api.timeline.forProfile>>;
export type Patterns = FunctionReturnType<typeof api.patterns.byEmployer>;
export type PayrollScript = "cooperate" | "stall_once" | "refuse_once";

export const usd = (cents: number) =>
  (cents / 100).toLocaleString("en-US", { style: "currency", currency: "USD" });
export const time = (iso: string) =>
  new Date(iso).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
export const day = (isoDate: string) => {
  // Dates written by the voice agent may not be ISO; show those as given instead of "Invalid Date".
  if (!/^\d{4}-\d{2}-\d{2}/.test(isoDate)) return isoDate;
  return new Date(isoDate + (isoDate.length === 10 ? "T12:00:00" : "")).toLocaleDateString("en-US", { month: "short", day: "numeric" });
};

export const SS_BP = 620; // 6.20%
export const MEDICARE_BP = 145; // 1.45%
export const pct = (cents: number, bp: number) => Math.floor((cents * bp + 5000) / 10000);

/** Calendar-year number on F-1 for a given year: arriving in 2024 makes 2024 year 1. Display only; the rules engine decides. */
export const calendarYear = (arrivalDate: string, year: number) => year - Number(arrivalDate.slice(0, 4)) + 1;

export const AGENT_LABEL: Record<string, string> = {
  coordinator: "Coordinator",
  ledger: "Ledger",
  tax: "Rules",
  caseworker: "Caseworker",
  voice: "Voice",
  seed: "Setup",
};

export const ACTION_LABEL: Record<string, string> = {
  reset_demo: "Demo reset",
  recorded_transactions: "Bank activity recorded",
  recorded_paystub: "Paystub organized",
  paystub_skipped: "Paystub already on file",
  paystub_unreadable: "Paystub could not be read",
  flag_written: "Flag written",
  flag_blocked: "Flag blocked",
  quote_rejected: "Quote rejected",
  rule_not_triggered: "Rule checked, nothing found",
  open_flags_listed: "Open items sent to Priya",
  check_pay_requested: "Priya asked to check her pay",
  approval_received: "Priya approved",
  approval_declined: "Priya declined",
  quote_accepted: "Quote verified",
  source_fetched: "Official source fetched",
  call_requested: "Call requested",
  call_placed: "Calling payroll",
  case_written_request: "Written request needed",
  written_request_prepared: "Written request prepared",
  simulated_cohort: "Simulated students added",
  call_failed: "Call could not start",
  refund_matched: "Refund deposit matched",
  case_open: "Case opened",
  case_awaiting_approval: "Waiting for approval",
  case_contacting_employer: "Contacting payroll",
  case_awaiting_response: "Waiting on payroll",
  case_refund_received: "Refund received",
  case_closed: "Case closed",
  case_escalate_irs: "Escalated to the IRS",
};
export const actionLabel = (a: string) => ACTION_LABEL[a] ?? a.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());

export const RULE_LABEL: Record<string, string> = {
  FICA_EXEMPT_F1: "Social Security and Medicare withheld",
  ONCAMPUS_20_HOURS: "Over 20 hours in one week",
  FORM_8843_ANNUAL: "Form 8843 due",
};

// ---------- Demo copy: synthetic, mirrors seed/demo_data.py and rules/rules.yaml ----------

const NOW = Date.now();
const ago = (min: number) => new Date(NOW - min * 60000).toISOString();
const id = <T extends TableNames>(s: string) => s as unknown as Id<T>;

const PROFILE_ID = id<"profiles">("demo_profile");
const FICA_SOURCE = id<"sources">("demo_src_p519");
const HOURS_SOURCE = id<"sources">("demo_src_cfr");
const FICA_FLAG = id<"flags">("demo_flag_fica");
const CASE_ID = id<"cases">("demo_case");

function stubs(): Paystub[] {
  const out: Paystub[] = [];
  const first = new Date("2026-01-12T12:00:00");
  for (let i = 1; i <= 8; i++) {
    const start = new Date(first.getTime() + 14 * (i - 1) * 86400000);
    const end = new Date(start.getTime() + 13 * 86400000);
    const hours = i === 5 ? [16, 24] : [20, 20];
    const gross = (hours[0] + hours[1]) * 1800;
    const ss = pct(gross, SS_BP), med = pct(gross, MEDICARE_BP);
    out.push({
      _id: id<"paystubs">(`demo_stub_${i}`), _creationTime: NOW - (60 - i) * 60000, profileId: PROFILE_ID,
      periodStart: start.toISOString().slice(0, 10), periodEnd: end.toISOString().slice(0, 10),
      employer: "University Dining Services", grossCents: gross, hoursByWeek: hours,
      ssCents: ss, medicareCents: med, netCents: gross - ss - med, sourceFile: `paystub_${String(i).padStart(2, "0")}.pdf`,
    });
  }
  return out;
}

export const DRAFT =
  "Hello, I'm writing for Priya Sharma, an F-1 student in her third calendar year in the US. Social Security ($357.12) and " +
  "Medicare ($83.52) were withheld across her 8 paychecks from Jan 12 to May 3, 2026. Nonresident F-1 students are " +
  "generally exempt from both. Could you refund $440.64 and update her tax status so future pay isn't withheld?";

// Demo copy of the Caseworker's letter (agents/caseworker/engine.py draft_written_request).
export function demoLetter(nextFollowUp: string): string {
  const today = new Date();
  const long = (d: Date) => d.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });
  return `${long(today)}\n\nTo: University Dining Services Payroll\nRe: Refund of Social Security and Medicare withheld in error, Priya Sharma\n\n` +
    "Docket, an AI assistant acting for Priya Sharma with her permission, called payroll about this refund. Payroll did not agree to refund it on that call, so this letter puts the request in writing.\n\n" +
    "Priya Sharma is a nonresident alien student in F-1 status, in calendar year 3 of 5 in the United States. Social Security ($357.12) and Medicare ($83.52) were withheld from 8 paychecks for pay periods 2026-01-12 to 2026-05-03, a total of $440.64.\n\n" +
    "IRS Publication 519, U.S. Tax Guide for Aliens states: \"Social security and Medicare taxes are not withheld from pay for the work unless the student is considered a resident alien.\"\n\n" +
    `Please, by ${long(new Date(today.getTime() + 10 * 86400000))}, do one of the following:\n1. Refund $440.64 and stop withholding Social Security and Medicare from her future paychecks; or\n` +
    "2. If you will not refund it, give her a written statement saying so. She needs that statement to claim the refund from the IRS with Form 843 and Form 8316.\n\n" +
    `Docket will follow up by phone on ${nextFollowUp}.\n\nSent by Priya Sharma, prepared with Docket.`;
}

export function demoSnapshot(): Snapshot {
  const paystubs = stubs();
  const transactions = paystubs.map((p, k) => ({
    _id: id<"transactions">(`demo_tx_${k}`), _creationTime: NOW, profileId: PROFILE_ID, kind: "deposit",
    amountCents: p.netCents, date: new Date(new Date(p.periodEnd + "T12:00:00").getTime() + (1 + (k % 2)) * 86400000).toISOString().slice(0, 10),
    counterparty: "University Dining Payroll", memo: `Payroll ${p.periodStart} to ${p.periodEnd}`, nessieId: `demo_${k}`,
  })).reverse();
  return {
    profile: {
      _id: PROFILE_ID, _creationTime: NOW, name: "Priya Sharma", visa: "F-1", arrivalDate: "2024-08-15",
      school: "Golden Bear University", homeCountry: "India", homeCurrency: "INR", workAuth: "on-campus",
      phoneMasked: "(***) ***-4821", filed8843Years: [2024, 2025],
    },
    flags: [
      {
        _id: FICA_FLAG, _creationTime: NOW, profileId: PROFILE_ID, ruleId: "FICA_EXEMPT_F1", amountCents: 44064,
        explanation: "You are likely exempt from Social Security and Medicare tax (calendar year 3 of 5 on F-1), but $440.64 was withheld. You can likely get it refunded. Confirm with your school's international office.",
        quote: "Social security and Medicare taxes are not withheld from pay for the work unless the student is considered a resident alien.",
        sourceId: FICA_SOURCE, status: "case_opened",
        sourceTitle: "IRS Publication 519, U.S. Tax Guide for Aliens", sourceUrl: "https://www.irs.gov/publications/p519",
        sourceFetchedAt: ago(90), sourceHash: "demo",
      },
      {
        _id: id<"flags">("demo_flag_hours"), _creationTime: NOW, profileId: PROFILE_ID, ruleId: "ONCAMPUS_20_HOURS", amountCents: 0,
        explanation: "You likely worked 24 hours the week of 2026-03-16 (Spring 2026), over the 20-hour weekly limit while school is in session. Confirm with your school's international office.",
        quote: "Employment authorized under this paragraph (f)(9)(i) must not exceed 20 hours a week while school is in session",
        sourceId: HOURS_SOURCE, status: "open",
        sourceTitle: "8 CFR 214.2(f)(9)(i), on-campus employment", sourceUrl: "https://www.ecfr.gov/current/title-8/section-214.2",
        sourceFetchedAt: ago(90), sourceHash: "demo",
      },
    ],
    cases: [{
      _id: CASE_ID, _creationTime: NOW, flagId: FICA_FLAG, profileId: PROFILE_ID, state: "awaiting_approval",
      amountCents: 44064, nextFollowUp: new Date(NOW + 86400000).toISOString().slice(0, 10), draft: DRAFT, calls: [],
    }],
    paystubs,
    transactions,
  };
}

const row = (n: number, agent: string, action: string, detail: string, min: number): Activity => ({
  _id: id<"activity">(`demo_act_${n}`), _creationTime: NOW - min * 60000, agent, action, detail, at: ago(min),
});

export function demoFeed(): Activity[] {
  const stubRows = stubs().map((p, k) => row(3 + k, "ledger", "recorded_paystub", `${p.sourceFile}: ${usd(p.grossCents)} gross, ${p.hoursByWeek.join(" + ")} hours. Math checked: 6.2% and 1.45% of gross.`, 40 - k));
  return [
    row(1, "seed", "reset_demo", "Wiped demo tables; seeded Priya Sharma. The Ledger records paystubs from the PDFs.", 44),
    row(2, "ledger", "recorded_transactions", "31 bank rows from Capital One Nessie; 8 payroll deposits of $664.92.", 42),
    ...stubRows,
    row(11, "tax", "quote_rejected", "FICA_EXEMPT_F1: quote not found word for word in the stored source. Not shown to Priya.", 30),
    row(12, "tax", "flag_written", "FICA_EXEMPT_F1: $440.64 withheld in calendar year 3 of 5. Quote verified in IRS Publication 519.", 29),
    row(13, "tax", "flag_written", "ONCAMPUS_20_HOURS: 24 hours the week of 2026-03-16, Spring 2026 in session. Quote verified in 8 CFR 214.2.", 28),
    row(14, "tax", "rule_not_triggered", "FORM_8843_ANNUAL: filings on record for 2024 and 2025.", 28),
    row(15, "caseworker", "case_open", "Refund case opened for $440.64", 26),
    row(16, "caseworker", "case_awaiting_approval", "Draft request written; waiting for the student's approval", 26),
  ].reverse();
}
