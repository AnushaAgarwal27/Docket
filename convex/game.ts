import { mutation, query } from "./_generated/server";

const FICA = "FICA_EXEMPT_F1";

// A browser cannot send a uAgent message, so the game asks for a hearing by leaving a row here and
// the Tax agent picks it up on its next pass. Without this the game replayed the hearing the agents
// held earlier, which looks identical on screen but means nothing is running while you watch: the
// Agentverse interaction counts stay flat and the agents are a recording, not a system.
export const requestHearing = mutation({
  args: {},
  handler: async (ctx) => {
    const profiles = await ctx.db.query("profiles").take(20);
    const profile = profiles.find((p) => !p.simulated);
    if (profile === undefined) return null;
    // activity.at and hearings.createdAt are both ISO strings, and the comparison below is a
    // string comparison, which only orders correctly because ISO-8601 sorts lexicographically.
    const at = new Date().toISOString();
    const id = await ctx.db.insert("activity", {
      agent: "game",
      action: "hearing_requested",
      detail: "The Hearing game asked the agents to hold this hearing again, live",
      at,
    });
    return { requestedAt: at, id };
  },
});

// The Tax agent polls this. True when a hearing was asked for after the newest hearing was held,
// so a request is answered exactly once however often the game is opened.
export const hearingRequested = query({
  args: {},
  handler: async (ctx) => {
    const profiles = await ctx.db.query("profiles").take(20);
    const profile = profiles.find((p) => !p.simulated);
    if (profile === undefined) return { requested: false, profileId: null };

    const asks = await ctx.db
      .query("activity")
      .order("desc")
      .filter((q) => q.eq(q.field("action"), "hearing_requested"))
      .take(1);
    if (asks.length === 0) return { requested: false, profileId: profile._id };

    const hearings = await ctx.db
      .query("hearings")
      .withIndex("by_profile", (q) => q.eq("profileId", profile._id))
      .order("desc")
      .take(1);
    const heldAt = hearings.length ? hearings[0].createdAt : "";
    return { requested: asks[0].at > heldAt, profileId: profile._id };
  },
});

// The live case file the Hearing game (docket-game.html) plays: the demo student, the FICA finding,
// the hearing the agents actually held, and what the case, the payroll call and the bank say now.
// Read through Convex's HTTP query API, so the game needs no client library. Null pieces mean the
// agents have not got that far yet; the game then shows what exists and says what is pending.
export const caseFile = query({
  args: {},
  handler: async (ctx) => {
    const profiles = await ctx.db.query("profiles").take(20);
    const profile = profiles.find((p) => !p.simulated);
    if (profile === undefined) return null;

    const flags = await ctx.db
      .query("flags")
      .withIndex("by_profile", (q) => q.eq("profileId", profile._id))
      .order("desc")
      .take(50);
    const flag = flags.find((f) => f.ruleId === FICA) ?? null;

    const hearings = await ctx.db
      .query("hearings")
      .withIndex("by_profile", (q) => q.eq("profileId", profile._id))
      .order("desc")
      .take(20);
    const hearing = hearings.find((h) => h.ruleId === FICA && (flag === null || h.flagId === flag._id)) ?? null;

    const source = flag ? await ctx.db.get(flag.sourceId) : null;
    const firstStub = flag?.paystubIds?.length ? await ctx.db.get(flag.paystubIds[0]) : null;
    const theCase = flag
      ? await ctx.db.query("cases").withIndex("by_flag", (q) => q.eq("flagId", flag._id)).order("desc").first()
      : null;
    const call = theCase
      ? await ctx.db.query("calls").withIndex("by_case", (q) => q.eq("caseId", theCase._id)).order("desc").first()
      : null;

    return {
      student: {
        name: profile.name,
        visa: profile.visa,
        arrivalDate: profile.arrivalDate,
        employer: profile.employer ?? null,
      },
      finding: flag && {
        amountCents: flag.amountCents,
        ssCents: flag.ssCents ?? null,
        medicareCents: flag.medicareCents ?? null,
        paychecks: flag.paystubIds?.length ?? null,
        payYear: firstStub ? Number(firstStub.periodEnd.slice(0, 4)) : null,
        employer: firstStub?.employer ?? null,
        quote: flag.quote,
        sourceTitle: source?.title ?? null,
        status: flag.status,
      },
      hearing: hearing && {
        rounds: hearing.rounds.map((r) => ({ side: r.side, objectionId: r.objectionId ?? null, argument: r.argument })),
        verdict: hearing.verdict,
        reason: hearing.reason,
        at: hearing.createdAt,
      },
      case: theCase && {
        id: theCase._id,
        state: theCase.state,
        amountCents: theCase.amountCents,
        outcome: theCase.outcome ?? null,
        callAttempts: theCase.callAttempts ?? 0,
        writtenRequest: theCase.writtenRequestAt !== undefined,
        callError: theCase.callError ?? null,
      },
      call: call && {
        answeredBy: call.answeredBy,
        summary: call.summary,
        promisedBy: call.promisedBy ?? null,
        referenceNo: call.referenceNo ?? null,
        at: call.at,
      },
    };
  },
});
