import { query } from "./_generated/server";
import { v } from "convex/values";

// The student's timeline across years, built from the rows in the student file, plus the next thing
// coming up ("next season"). `today` is passed in because queries must not read the clock.
// Deadlines mirror rules/rules.py needs_8843: April 15 when the student had US wages that year
// (filed with Form 1040-NR), otherwise June 15. Weekend and holiday shifts are not applied.

type Tone = "done" | "warn" | "info" | "next";
type Event = { date: string; title: string; detail: string; tone: Tone; upcoming: boolean };

const EXEMPT_YEARS = 5;
const usd = (cents: number) =>
  "$" + (cents / 100).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const longDate = (iso: string) =>
  new Date(iso.slice(0, 10) + "T12:00:00Z").toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric", timeZone: "UTC" });

export const forProfile = query({
  args: { profileId: v.id("profiles"), today: v.string() },
  handler: async (ctx, { profileId, today }) => {
    const profile = await ctx.db.get(profileId);
    if (profile === null) return null;
    const thisYear = Number(today.slice(0, 4));
    const arrivalYear = Number(profile.arrivalDate.slice(0, 4));
    const lastExemptYear = arrivalYear + EXEMPT_YEARS - 1;
    const paystubs = await ctx.db.query("paystubs").withIndex("by_profile", (q) => q.eq("profileId", profileId)).take(100);
    const flags = await ctx.db.query("flags").withIndex("by_profile", (q) => q.eq("profileId", profileId)).take(50);
    const cases = await ctx.db.query("cases").withIndex("by_profile", (q) => q.eq("profileId", profileId)).take(50);
    const transactions = await ctx.db.query("transactions").withIndex("by_profile", (q) => q.eq("profileId", profileId)).take(500);
    const filed = new Set(profile.filed8843Years ?? []);
    const wageYears = new Set(paystubs.filter((p) => p.grossCents > 0).map((p) => Number(p.periodEnd.slice(0, 4))));
    const events: Event[] = [];

    events.push({
      date: profile.arrivalDate, title: `Arrived on ${profile.visa}`, tone: "info", upcoming: false,
      detail: `Calendar year 1 of ${EXEMPT_YEARS} on ${profile.visa}. Any part of a year counts as a full year.`,
    });
    for (let y = arrivalYear; y < thisYear; y++) {
      const due = `${y + 1}-${wageYears.has(y) ? "04" : "06"}-15`;
      events.push(filed.has(y)
        ? { date: due, title: `Form 8843 for ${y} on record`, detail: `Was due ${longDate(due)}.`, tone: "done", upcoming: false }
        : { date: due, title: `Form 8843 for ${y} not on record`, detail: `Was due ${longDate(due)}. Every exempt year needs one, even with no income.`, tone: "warn", upcoming: false });
    }
    const byYear = new Map<number, typeof paystubs>();
    for (const p of paystubs) {
      const y = Number(p.periodStart.slice(0, 4));
      byYear.set(y, [...(byYear.get(y) ?? []), p]);
    }
    for (const [y, stubs] of [...byYear.entries()].sort((a, b) => a[0] - b[0])) {
      const first = stubs.map((p) => p.periodStart).sort()[0];
      const withheld = stubs.reduce((s, p) => s + p.ssCents + p.medicareCents, 0);
      events.push({
        date: first, title: `Worked at ${stubs[0].employer}`, tone: "info", upcoming: false,
        detail: `${stubs.length} paychecks in ${y}, calendar year ${y - arrivalYear + 1} of ${EXEMPT_YEARS}. ${usd(withheld)} withheld for Social Security and Medicare.`,
      });
    }
    for (const f of flags) {
      events.push({
        date: new Date(f._creationTime).toISOString(), tone: f.status === "resolved" ? "done" : "warn", upcoming: false,
        title: f.ruleId === "FICA_EXEMPT_F1" ? `Docket found ${usd(f.amountCents)} withheld in error` : f.ruleId === "ONCAMPUS_20_HOURS" ? "Docket flagged a week over 20 hours" : "Docket flagged a missing Form 8843",
        detail: f.status === "resolved" ? "Resolved." : "Verified against the official source.",
      });
    }
    for (const c of cases) {
      const calls = await ctx.db.query("calls").withIndex("by_case", (q) => q.eq("caseId", c._id)).take(10);
      for (const call of calls) {
        events.push({ date: call.at, title: "Payroll call", detail: call.summary, tone: "info", upcoming: false });
      }
      if (c.writtenRequestAt) {
        events.push({ date: c.writtenRequestAt, title: "Written request prepared", detail: "For the student to send to payroll.", tone: "info", upcoming: false });
      }
      if (["contacting_employer", "awaiting_response", "written_request"].includes(c.state)) {
        events.push({ date: c.nextFollowUp, title: "Docket follows up with payroll", detail: `Refund case for ${usd(c.amountCents)}.`, tone: "next", upcoming: true });
      }
    }
    for (const t of transactions) {
      if (t.memo === "FICA refund") {
        events.push({ date: t.date, title: `Refund received: ${usd(t.amountCents)}`, detail: `From ${t.counterparty}.`, tone: "done", upcoming: false });
      }
    }

    // Next season: this year's filing, then the end of the exempt window.
    const hadWages = wageYears.has(thisYear);
    const due = `${thisYear + 1}-${hadWages ? "04" : "06"}-15`;
    const nextSeason = {
      date: due,
      title: `Next tax season: file for ${thisYear} by ${longDate(due)}`,
      detail: hadWages
        ? `File Form 1040-NR and Form 8843 for ${thisYear}, since there were US wages this year. Docket will remind you in March.`
        : `File Form 8843 for ${thisYear}, even with no income. Docket will remind you in May.`,
    };
    events.push({ date: due, title: `Form 8843${hadWages ? " and 1040-NR" : ""} for ${thisYear} due`, detail: nextSeason.detail, tone: "next", upcoming: true });
    if (thisYear <= lastExemptYear) {
      events.push({
        date: `${lastExemptYear + 1}-01-01`, title: `Calendar year ${EXEMPT_YEARS + 1} begins`, tone: "next", upcoming: true,
        detail: `From ${lastExemptYear + 1}, Social Security and Medicare withholding is likely correct, so Docket stops flagging it. Some students qualify to stay exempt longer; ask your international office.`,
      });
    }
    events.sort((a, b) => a.date.localeCompare(b.date));
    return { events, nextSeason, calendarYear: thisYear - arrivalYear + 1, lastExemptYear };
  },
});
