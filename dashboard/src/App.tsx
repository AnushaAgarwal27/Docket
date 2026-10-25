import { Component, Suspense, lazy, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { useMutation, useQuery } from "convex/react";
import { api } from "../../convex/_generated/api";
import type { Id } from "../../convex/_generated/dataModel";
import type { Activity, Case, Patterns, PayrollScript, Snapshot, Timeline } from "./data";
import { AGENT_LABEL, MEDICARE_BP, RULE_LABEL, SS_BP, actionLabel, calendarYear, day, demoFeed, demoLetter, demoSnapshot, pct, time, usd } from "./data";
import { PaperTrail } from "./PaperTrail";
import { TracksView } from "./Tracks";

// three.js loads separately, so the page renders before the 3D does.
const EvidenceStack = lazy(() => import("./EvidenceStack").then((m) => ({ default: m.EvidenceStack })));

// Live mode reads the shared student file from Convex: Anusha's snapshot query, the activity feed,
// the timeline and the employer pattern. Demo mode (?demo) renders from labelled synthetic data, as an
// offline backup for rehearsals and the video; the timeline and pattern panels are live only.

type Mode = "live" | "demo";
type Tab = "overview" | "paystubs" | "cases" | "activity" | "tracks";
type Actions = {
  onApprove?: (caseId: Id<"cases">) => Promise<void>;
  onFollowUp?: (caseId: Id<"cases">) => Promise<void>;
  onSetScript?: (caseId: Id<"cases">, script: PayrollScript) => Promise<void>;
  onSimulateRefund?: () => void;
  onReset?: () => void;
};
type Extra = { timeline?: Timeline | null; patterns?: Patterns };

const localToday = () => new Date().toLocaleDateString("en-CA"); // YYYY-MM-DD in the viewer's time zone

export function LiveApp() {
  const profiles = useQuery(api.profiles.list);
  // The simulated cohort (employer pattern view) is never the student on screen.
  const profileId = profiles?.find((p) => !p.simulated)?._id;
  const snap = useQuery(api.dashboard.snapshot, profileId ? { profileId } : "skip");
  // Timeline and pattern load in guarded children: if the backend doesn't have those functions yet,
  // only those two panels go missing instead of the whole page.
  const [timeline, setTimeline] = useState<Timeline | null | undefined>(undefined);
  const [patterns, setPatterns] = useState<Patterns | undefined>(undefined);
  const feed = useQuery(api.activity.recent, { limit: 400 }); // the Tracks tab counts actions per agent
  const approve = useMutation(api.cases.approve);
  const followUp = useMutation(api.cases.followUp);
  const setScript = useMutation(api.cases.setPayrollScript);
  const state = profiles === undefined ? undefined : profileId === undefined ? null : snap;
  return (
    <>
    <Guard>{profileId && <TimelineFeed profileId={profileId} onData={setTimeline} />}</Guard>
    <Guard><PatternsFeed onData={setPatterns} /></Guard>
    <Dashboard mode="live" snap={state} feed={feed} timeline={timeline} patterns={patterns}
      onApprove={async (caseId) => { await approve({ caseId }); }}
      onFollowUp={async (caseId) => { await followUp({ caseId }); }}
      onSetScript={async (caseId, script) => { await setScript({ caseId, script }); }} />
    </>
  );
}

class Guard extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch(e: Error) { console.warn("Optional panel unavailable (is the backend deployed?):", e.message); }
  render() { return this.state.failed ? null : this.props.children; }
}

function TimelineFeed({ profileId, onData }: { profileId: Id<"profiles">; onData: (t: Timeline | null | undefined) => void }) {
  const t = useQuery(api.timeline.forProfile, { profileId, today: localToday() });
  useEffect(() => onData(t), [t, onData]);
  return null;
}

function PatternsFeed({ onData }: { onData: (p: Patterns | undefined) => void }) {
  const p = useQuery(api.patterns.byEmployer, {});
  useEffect(() => onData(p), [p, onData]);
  return null;
}

export function DemoApp() {
  const [snap, setSnap] = useState<Snapshot>(demoSnapshot);
  const [feed, setFeed] = useState<Activity[]>(demoFeed);
  const timers = useRef<number[]>([]);
  const snapRef = useRef(snap);
  snapRef.current = snap;
  useEffect(() => () => timers.current.forEach(clearTimeout), []);

  const clock = useRef(0); // strictly increasing times, so rows logged in the same millisecond keep their order
  const push = (agent: string, action: string, detail: string) => {
    clock.current = Math.max(Date.now(), clock.current + 1);
    const at = clock.current;
    setFeed((f) => [{ _id: `demo_${at}_${f.length}` as Id<"activity">, _creationTime: at, agent, action, detail, at: new Date(at).toISOString() }, ...f]);
  };
  const patchCase = (fn: (c: Case) => Case) => setSnap((s) => ({ ...s, cases: s.cases.map(fn) }));
  const inDays = (n: number) => new Date(Date.now() + n * 86400000).toISOString().slice(0, 10);

  // One simulated payroll call, following the case's rehearsal setting on the first attempt.
  const runCall = (attempt: number) => {
    push("voice", "call_placed", "Calling payroll (demo). The agent says it is an AI assistant acting with Priya's permission.");
    timers.current.push(window.setTimeout(() => {
      {
        const s = snapRef.current;
        const c0 = s.cases[0];
        const script = c0.payrollScript ?? "cooperate";
        const result = attempt > 1 || script === "cooperate" ? "promised" : script === "stall_once" ? "stalled" : "refused";
        const promised = inDays(14);
        const call = {
          _id: `demo_call_${attempt}` as Id<"calls">, _creationTime: Date.now(), caseId: c0._id, answeredBy: "Payroll office", at: new Date().toISOString(),
          summary: result === "promised" ? "Confirmed the F-1 status on file; will refund the Social Security and Medicare withheld and stop withholding."
            : result === "stalled" ? "Said they would look into it but would not give a date." : "Said they cannot refund taxes already reported.",
          ...(result === "promised" ? { promisedBy: promised, referenceNo: "PR-88213" } : {}),
        };
        const next: Case = result === "promised"
          ? { ...c0, state: "awaiting_response", nextFollowUp: promised, calls: [call, ...c0.calls] }
          : { ...c0, state: "written_request", nextFollowUp: inDays(3), writtenRequest: demoLetter(inDays(3)), writtenRequestAt: new Date().toISOString(), calls: [call, ...c0.calls] };
        setSnap({ ...s, cases: [{ ...next, callAttempts: attempt }] });
        if (result === "promised") push("caseworker", "case_awaiting_response", `Payroll promised a refund by ${promised}`);
        else {
          push("caseworker", "case_written_request", `Payroll ${result === "stalled" ? "would not commit to a date" : "refused"} on call 1; putting the request in writing`);
          push("caseworker", "written_request_prepared", "Written request prepared for Priya to send; phone follow-up in 3 days");
        }
      }
    }, 2600));
  };

  const actions: Actions = {
    onApprove: async () => {
      patchCase((c) => ({ ...c, state: "contacting_employer" }));
      push("coordinator", "approval_recorded", "Priya replied YES. Approval recorded; nothing was sent before this.");
      push("caseworker", "case_contacting_employer", "Student approved; contacting payroll");
      runCall(1);
    },
    onFollowUp: async () => {
      patchCase((c) => ({ ...c, state: "contacting_employer" }));
      push("caseworker", "case_contacting_employer", "Following up by phone on the written request");
      runCall(2);
    },
    onSetScript: async (_caseId, script) => patchCase((c) => ({ ...c, payrollScript: script })),
    onSimulateRefund: () => {
      const today = new Date().toISOString().slice(0, 10);
      setSnap((s) => ({
        ...s,
        transactions: [{ _id: "demo_refund" as Id<"transactions">, _creationTime: Date.now(), profileId: s.profile._id, kind: "deposit", amountCents: 44064, date: today, counterparty: "University Dining Payroll", memo: "FICA refund", nessieId: "demo_refund" }, ...s.transactions],
        flags: s.flags.map((f) => (f.ruleId === "FICA_EXEMPT_F1" ? { ...f, status: "resolved" } : f)),
        cases: s.cases.map((c) => ({ ...c, state: "closed", outcome: "refunded" })),
      }));
      push("ledger", "refund_matched", "Deposit of $440.64 from University Dining Payroll, memo “FICA refund”, matches case within $1.");
      push("caseworker", "case_refund_received", "Refund deposit matched");
      push("caseworker", "case_closed", "Refund received; case closed");
    },
    onReset: () => {
      timers.current.forEach(clearTimeout); timers.current = [];
      setSnap(demoSnapshot()); setFeed(demoFeed());
    },
  };
  return <Dashboard mode="demo" snap={snap} feed={feed} {...actions} />;
}

const TABS: [Tab, string][] = [["overview", "Overview"], ["paystubs", "Paystubs"], ["cases", "Cases"], ["activity", "Activity"], ["tracks", "Tracks"]];

function useWide(px: number) {
  const q = `(min-width: ${px}px)`;
  const [wide, setWide] = useState(() => matchMedia(q).matches);
  useEffect(() => {
    const m = matchMedia(q);
    const on = () => setWide(m.matches);
    m.addEventListener("change", on);
    return () => m.removeEventListener("change", on);
  }, [q]);
  return wide;
}

function Dashboard({ mode, snap, feed, timeline, patterns, ...actions }: { mode: Mode; snap: Snapshot | null | undefined; feed: Activity[] | undefined } & Extra & Actions) {
  const initial = (location.hash.slice(1) as Tab) || "overview";
  const [tab, setTab] = useState<Tab>(TABS.some(([t]) => t === initial) ? initial : "overview");
  const [sel, setSel] = useState<number | null>(null);
  const wide = useWide(1000);
  useEffect(() => { history.replaceState(null, "", tab === "overview" ? location.pathname + location.search : `#${tab}`); }, [tab]);

  const go = (t: Tab) => { setTab(t); window.scrollTo({ top: 0 }); };
  const stubs = useMemo(() => (snap ? [...snap.paystubs].sort((a, b) => a.periodStart.localeCompare(b.periodStart)) : []), [snap]);
  const selected = sel ?? stubs.length - 1;
  const inspect = (k: number) => {
    setSel(k);
    if (tab !== "overview" && tab !== "paystubs") setTab("overview");
    requestAnimationFrame(() => document.getElementById("paper-trail")?.scrollIntoView({ behavior: "smooth", block: "start" }));
  };

  return (
    <div className="app">
      <header className="nav">
        <div className="nav-in">
          <div className="brand"><Mark /><span>docket</span></div>
          <nav className="tabs" aria-label="Sections">
            {TABS.map(([t, label]) => (
              <button key={t} type="button" className={tab === t ? "on" : ""} aria-current={tab === t ? "page" : undefined} onClick={() => go(t)}>
                <Icon name={t} />{label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      <div className="page">
        <div className="crumbs">
          <span>Workspace <span className="sep">/</span> <b>{TABS.find(([t]) => t === tab)![1]}</b></span>
          <span className="crumb-r">
            {mode === "live" ? <span className="pill live"><i />Live · shared student file</span> : <span className="pill demo"><i />Demo data, synthetic</span>}
            <span className="avatar" title={snap?.profile.name}>{snap ? initials(snap.profile.name) : "··"}</span>
          </span>
        </div>

        {snap === undefined && <Loading />}
        {snap === null && (
          <div className="empty-state">
            <h1>No student file yet.</h1>
            <p className="muted">Seed Priya with <code>python -m seed.reset</code>, then say “check my pay” in ASI:One. This page fills in as each agent writes.</p>
          </div>
        )}
        {snap && tab === "overview" && <SourceUpdate feed={feed} onTab={go} />}
        {snap && tab === "overview" && <Overview snap={snap} stubs={stubs} feed={feed} selected={selected} onSelect={inspect} onTab={go} mode={mode} wide={wide} timeline={timeline} patterns={patterns} {...actions} />}
        {snap && tab === "paystubs" && <PaystubsView snap={snap} stubs={stubs} selected={selected} onSelect={inspect} wide={wide} />}
        {snap && tab === "cases" && <CasesView snap={snap} mode={mode} {...actions} />}
        {snap && tab === "activity" && <DocketView feed={feed} />}
        {snap && tab === "tracks" && <TracksView snap={snap} feed={feed} patterns={patterns} mode={mode} onTab={go} />}

        <footer className="foot">
          <span>{mode === "demo" ? "Demo mode: synthetic data, simulated calls and deposits. Nothing leaves this page." : "Live: every row comes from the shared Convex student file."}</span>
          <span>Docket · a caseworker for F-1 students</span>
        </footer>
      </div>
    </div>
  );
}

function Overview({ snap, stubs, feed, selected, onSelect, onTab, mode, wide, timeline, patterns, ...actions }: {
  snap: Snapshot; stubs: Snapshot["paystubs"]; feed: Activity[] | undefined; selected: number; onSelect: (k: number) => void; onTab: (t: Tab) => void; mode: Mode; wide: boolean;
} & Extra & Actions) {
  const { profile, flags, cases } = snap;
  const fica = flags.find((f) => f.ruleId === "FICA_EXEMPT_F1");
  const refundCase = cases.find((c) => c.flagId === fica?._id) ?? cases[0];
  const closed = refundCase?.state === "closed" && refundCase.outcome === "refunded";
  const withheld = stubs.reduce((s, p) => s + p.ssCents + p.medicareCents, 0);
  const net = stubs.reduce((s, p) => s + p.netCents, 0);
  const openItems = flags.filter((f) => f.status !== "resolved");
  const overIdx = stubs.findIndex((p) => p.hoursByWeek.some((h) => h > 20));
  const hoursFlag = flags.find((f) => f.ruleId === "ONCAMPUS_20_HOURS");
  const matched = stubs.filter((p) => snap.transactions.some((t) => t.kind === "deposit" && t.amountCents === p.netCents)).length;
  const term = stubs.length ? termName(stubs[0].periodStart) : "No paystubs yet";
  const employer = stubs[0]?.employer ?? "No employer on file";
  let cum = 0;
  const bars = stubs.map((p) => (cum += p.ssCents + p.medicareCents));
  const amount = usd(fica?.amountCents ?? withheld);
  const lede = !fica
    ? "Docket hasn’t found anything yet. Say “check my pay” in ASI:One and the agents get to work."
    : closed ? `Your ${amount} refund is back in your account. The case is closed.`
    : refundCase?.state === "awaiting_approval" ? `We found ${amount} in Social Security and Medicare withheld in error across ${stubs.length} paychecks. Review the request before Docket contacts payroll.`
    : refundCase?.state === "contacting_employer" ? `Docket is contacting payroll about your ${amount} refund, as an AI assistant acting with your permission.`
    : refundCase?.state === "written_request" ? "Payroll didn’t commit on the first call. A written request is ready for you to send, and Docket will follow up by phone."
    : refundCase?.state === "awaiting_response" ? `Payroll promised your ${amount} refund${refundCase.calls[0]?.promisedBy ? ` by ${day(refundCase.calls[0].promisedBy)}` : ""}. Docket is watching your deposits.`
    : refundCase?.state === "escalate_irs" ? "Payroll won’t refund it. Your IRS claim checklist is ready."
    : `We found ${amount} withheld in error across ${stubs.length} paychecks.`;
  const scrollTo = (id: string) => document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });

  return (
    <>
      <section className="hero2">
        <div className="h2-copy">
          <span className="h2-eyebrow">{profile.name} · {profile.visa}, calendar year {calendarYear(profile.arrivalDate, new Date().getFullYear())} of 5 · {term} · {employer}</span>
          <h1>Your money, in focus.</h1>
          <p className="h2-lede">{lede}</p>
          <div className="h2-actions">
            <button type="button" className="btn" onClick={() => scrollTo("case-review")}>{refundCase?.state === "awaiting_approval" ? "Review the request" : refundCase ? "See the case" : "See the paystubs"}</button>
            <button type="button" className="btn ghost" onClick={() => scrollTo("paper-trail")}>See the evidence</button>
            {mode === "demo" && actions.onReset && <button type="button" className="btn ghost" onClick={actions.onReset}>↺ Reset demo</button>}
          </div>
          <div className="h2-stats">
            <div>
              <span className="kpi-l">{closed ? "Recovered" : "Withheld in error"}</span>
              <div className="kpi-row"><span className={`kpi-v num ${closed ? "okc" : fica ? "evc" : ""}`}>{usd(fica?.amountCents ?? (fica ? withheld : 0))}</span><Spark values={bars} done={closed} /></div>
              <span className="kpi-s">{fica ? `Across ${stubs.length} paychecks` : "Nothing flagged yet"}</span>
            </div>
            <div>
              <span className="kpi-l">Net pay recorded</span>
              <span className="kpi-v num">{usd(net)}</span>
              <span className="kpi-s">{matched} of {stubs.length} matched to a deposit</span>
            </div>
            <div>
              <span className="kpi-l">Items to review</span>
              <span className="kpi-v num">{openItems.length}</span>
              <span className="kpi-s">{openItems.length ? openItems.map((f) => shortRule(f.ruleId)).join(" + ") : "Nothing open"}</span>
            </div>
          </div>
        </div>
        <div className="h2-stage">
          {stubs.length > 0 ? (
            <Suspense fallback={<div className="es-stage" />}>
              <EvidenceStack stubs={stubs} flagged={!!fica} recovered={closed} totalCents={fica?.amountCents ?? withheld} selected={selected} onSelect={onSelect} />
            </Suspense>
          ) : <div className="es-stage es-empty"><p>No paystubs yet. The Ledger reads them when Priya asks “check my pay”.</p></div>}
          <div className="h2-hint"><span>{stubs.length} paystubs from the student file</span><span>Hover to lift · click to inspect</span></div>
        </div>
      </section>

      <div className="ov-grid">
        <div className="ov-main">
          {refundCase ? <CaseReview c={refundCase} mode={mode} {...actions} /> : (
            <section className="panel pad"><h2>No case yet</h2><p className="muted">When a rule finds money owed, the Caseworker opens a case here with a drafted request for Priya to approve.</p></section>
          )}
          {overIdx >= 0 && hoursFlag && (
            <section className="callout">
              <div className="callout-t"><span className="sq" />One week needs a closer look</div>
              <p>Paystub {String(overIdx + 1).padStart(2, "0")} shows {Math.max(...stubs[overIdx].hoursByWeek)} hours in one week while school was in session. This stays private to Priya and is never shared with payroll.</p>
              <button type="button" className="link" onClick={() => onSelect(overIdx)}>Inspect paystub {String(overIdx + 1).padStart(2, "0")} →</button>
            </section>
          )}
          <Receipt snap={snap} stubs={stubs} onSelect={onSelect} live={mode === "live"} />
        </div>

        <aside className="ov-side">
          <section className="panel">
            <div className="panel-h">
              <h2>Recent paystubs</h2>
              <button type="button" className="link" onClick={() => onTab("paystubs")}>View all {stubs.length} →</button>
            </div>
            <StubList stubs={stubs} selected={selected} onSelect={onSelect} limit={4} pinned={overIdx} />
          </section>
          <section className="panel">
            <div className="panel-h">
              <h2>Case activity</h2>
              <button type="button" className="link" onClick={() => onTab("activity")}>Full docket →</button>
            </div>
            <Docket feed={feed} limit={5} />
          </section>
          {patterns && <EmployerPatterns patterns={patterns} studentEmployer={stubs[0]?.employer} />}
        </aside>
      </div>

      {timeline && <TimelinePanel timeline={timeline} name={profile.name} />}
      {stubs[selected] && <PaperTrail snap={snap} stub={stubs[selected]} index={selected} wide={wide} />}
    </>
  );
}

// ---- Source update popup: the collector logs source_changed when an official page's text changes ----
const SEEN_KEY = "docket.seenSourceChange";
const readSeen = () => { try { return localStorage.getItem(SEEN_KEY); } catch { return null; } };

function SourceUpdate({ feed, onTab }: { feed: Activity[] | undefined; onTab: (t: Tab) => void }) {
  const [seen, setSeen] = useState(readSeen);
  const latest = feed?.find((a) => a.action === "source_changed");
  if (!latest || latest._id === seen) return null;
  const dismiss = () => {
    setSeen(latest._id);
    try { localStorage.setItem(SEEN_KEY, latest._id); } catch { /* the popup just comes back on reload */ }
  };
  const held = latest.detail.includes("on hold");
  return (
    <div className={`src-toast${held ? " held" : ""}`} role="status" aria-live="polite">
      <div className="src-toast-t"><span className="sq" />{held ? "A rule changed. Related flags are on hold." : "An official rule page was updated"}</div>
      <p>{latest.detail.split(" (sha256")[0]}.</p>
      <span className="src-toast-a">
        <button type="button" className="link" onClick={() => { dismiss(); onTab("activity"); }}>See activity →</button>
        <button type="button" className="link" onClick={dismiss}>Dismiss</button>
      </span>
      <span className="src-toast-when">{day(latest.at.slice(0, 10))} · {time(latest.at)}</span>
    </div>
  );
}

// ---- Receipt: each verified flag as the paystub line beside the clause that makes it a problem ----
function Receipt({ snap, stubs, onSelect, live }: { snap: Snapshot; stubs: Snapshot["paystubs"]; onSelect: (k: number) => void; live: boolean }) {
  const flags = snap.flags;
  if (!flags.length) return null;
  const ss = stubs.reduce((s, p) => s + p.ssCents, 0);
  const med = stubs.reduce((s, p) => s + p.medicareCents, 0);
  const lines = (ruleId: string): { label: string; value: string; stub?: number }[] => {
    if (ruleId === "FICA_EXEMPT_F1") {
      const okSS = stubs.every((p) => p.ssCents === pct(p.grossCents, SS_BP));
      const okMed = stubs.every((p) => p.medicareCents === pct(p.grossCents, MEDICARE_BP));
      return [
        { label: `Social Security, ${stubs.length} paystubs${okSS ? " · 6.20% of gross, checked" : ""}`, value: usd(ss), stub: stubs.length - 1 },
        { label: `Medicare, ${stubs.length} paystubs${okMed ? " · 1.45% of gross, checked" : ""}`, value: usd(med), stub: stubs.length - 1 },
      ];
    }
    if (ruleId === "ONCAMPUS_20_HOURS") {
      return stubs.flatMap((p, k) => p.hoursByWeek.flatMap((h, w) => (h > 20 ? [{
        label: `Paystub ${String(k + 1).padStart(2, "0")} · week of ${day(new Date(new Date(p.periodStart + "T12:00:00").getTime() + 7 * w * 86400000).toISOString().slice(0, 10))}`,
        value: `${h.toFixed(2)} hours`, stub: k,
      }] : [])));
    }
    return [{ label: "Form 8843 on record", value: "none" }];
  };
  return (
    <section className="panel receipt" aria-label="Receipt">
      <div className="panel-h">
        <div><h2>Receipt</h2><p className="muted">What Docket checked, and the exact words it checked against.</p></div>
      </div>
      {flags.map((f) => (
        <article key={f._id} className={`rc ${f.ruleId === "ONCAMPUS_20_HOURS" ? "risk" : ""}`}>
          <div className="rc-h">
            <span className="rc-t">{RULE_LABEL[f.ruleId] ?? f.ruleId}</span>
            <span className="chip ok">✓ Verified</span>
          </div>
          <div className="rc-lines">
            {lines(f.ruleId).map((l, i) => (
              <button key={i} type="button" className="rc-line" onClick={() => l.stub !== undefined && onSelect(l.stub)} disabled={l.stub === undefined}>
                <span>{l.label}</span><span className="num">{l.value}</span>
              </button>
            ))}
          </div>
          <blockquote className="rc-q">“{f.quote}”</blockquote>
          <div className="rc-src">
            {f.sourceUrl ? <a href={f.sourceUrl} target="_blank" rel="noreferrer">{f.sourceTitle ?? f.sourceUrl}</a> : <span>{f.sourceTitle}</span>}
            <span className="muted num">{f.sourceFetchedAt ? `stored ${day(f.sourceFetchedAt.slice(0, 10))}, ${time(f.sourceFetchedAt)}` : ""}{f.sourceHash ? ` · hash ${f.sourceHash.slice(0, 8)}` : ""}</span>
          </div>
          <p className="fine">Matched word for word against the stored official text before this flag could be shown.</p>
          {live && <ReceiptFiles flagId={f._id} />}
        </article>
      ))}
    </section>
  );
}

// ---- Receipt documents: the stored paystub PDFs this flag came from, and the drafted letter (Convex file storage) ----
function ReceiptFiles({ flagId }: { flagId: Id<"flags"> }) {
  const files = useQuery(api.files.forFlag, { flagId });
  if (!files) return null;
  const { paystubs, letters } = files;
  if (!paystubs.length && !letters.length) return null;
  return (
    <div className="rc-files">
      {paystubs.length > 0 && (
        <div className="rc-file-row">
          <span className="muted">Paystub{paystubs.length > 1 ? "s" : ""}</span>
          {paystubs.map((f) => f.url && (
            <a key={f._id} href={f.url} target="_blank" rel="noreferrer" className="rc-file">{f.filename}</a>
          ))}
        </div>
      )}
      <div className="rc-file-row">
        <span className="muted">Letter</span>
        {letters.length
          ? letters.map((f) => f.url && <a key={f._id} href={f.url} target="_blank" rel="noreferrer" className="rc-file">{f.filename}</a>)
          : <span className="muted">not drafted yet</span>}
      </div>
    </div>
  );
}

// ---- Employer pattern: same error across several students at one employer (simulated cohort) ----
function EmployerPatterns({ patterns, studentEmployer }: { patterns: Patterns; studentEmployer?: string }) {
  const rows = patterns.employers.filter((r) => r.students > 0);
  if (!rows.length) return null;
  const simulated = rows.reduce((s, r) => s + r.simulated, 0);
  return (
    <section className="panel patterns" aria-label="Employer pattern">
      <div className="panel-h">
        <div><h2>Same employer, same error</h2><p className="muted">Students flagged for Social Security and Medicare withholding.</p></div>
        {patterns.anySimulated && <span className="chip ev">Simulated data</span>}
      </div>
      <ul className="pt-list">
        {rows.map((r) => (
          <li key={r.employer} className={r.pattern ? "hot" : ""}>
            <div className="pt-row">
              <span className="pt-name">{r.employer}{r.employer === studentEmployer ? <small> · Priya’s employer</small> : null}</span>
              <span className="num pt-count">{r.flagged} of {r.students}</span>
            </div>
            <div className="pt-bar"><i style={{ width: `${(100 * r.flagged) / r.students}%` }} /></div>
            <div className="pt-sub num">{usd(r.withheldCents)} withheld across flagged students</div>
            {r.pattern && <p className="pt-note">{r.flagged} students, same error: likely a payroll setup problem, not a one-off. Worth raising with the international office.</p>}
          </li>
        ))}
      </ul>
      <p className="fine pad-x">Highlighted at {patterns.minForPattern} or more flagged students. {simulated ? `${simulated} of the students are simulated; ` : ""}every count comes from the same rules engine and quote checker as Priya’s flags.</p>
    </section>
  );
}

// ---- Timeline: the student's years on F-1, and what comes next ----
function TimelinePanel({ timeline, name }: { timeline: Timeline; name: string }) {
  const years = new Map<string, Timeline["events"]>();
  for (const e of timeline.events) {
    const y = e.date.slice(0, 4);
    years.set(y, [...(years.get(y) ?? []), e]);
  }
  const first = name.split(" ")[0];
  return (
    <section className="panel timeline" aria-label="Timeline">
      <div className="panel-h">
        <div><h2>{first}’s timeline</h2><p className="muted">Calendar year {timeline.calendarYear} of 5 on F-1. Built from the student file, plus what comes next.</p></div>
      </div>
      <div className="tl-next">
        <span className="tl-next-l">Next season</span>
        <b>{timeline.nextSeason.title}</b>
        <p>{timeline.nextSeason.detail}</p>
      </div>
      <div className="tl-years">
        {[...years.entries()].map(([y, events]) => {
          const todayAt = events.findIndex((e) => e.upcoming);
          return (
            <div key={y} className="tl-year">
              <div className="tl-y num">{y}</div>
              <ol>
                {events.map((e, i) => (
                  <li key={i} className={`tl-e t-${e.tone} ${e.upcoming ? "up" : ""} ${i === todayAt && events.some((x) => !x.upcoming) ? "after-today" : ""}`}>
                    <span className="tl-d num">{day(e.date.slice(0, 10))}</span>
                    <span className="tl-t">{e.title}</span>
                    <span className="tl-x">{e.detail}</span>
                  </li>
                ))}
              </ol>
            </div>
          );
        })}
      </div>
      <p className="fine pad-x">Deadlines are likely dates (weekend shifts not applied). Confirm with your international office.</p>
    </section>
  );
}

const FLOW = ["identified", "approved", "contacted", "refunded"] as const;
const FLOW_LABEL = { identified: "Identified", approved: "Approved", contacted: "Contacted", refunded: "Refunded" };
function flowIndex(state: string) {
  // How many of the four steps are complete.
  return ({ open: 1, awaiting_approval: 1, contacting_employer: 2, written_request: 2, awaiting_response: 3, escalate_irs: 3, refund_received: 4, closed: 4 } as Record<string, number>)[state] ?? 0;
}
function stateLabel(s: string) {
  return ({ open: "Opened", awaiting_approval: "Needs approval", contacting_employer: "Contacting payroll", written_request: "Written request", awaiting_response: "Waiting on payroll", refund_received: "Refund received", closed: "Closed", escalate_irs: "Escalated to IRS" } as Record<string, string>)[s] ?? s;
}

const SCRIPTS: [PayrollScript, string, string][] = [
  ["cooperate", "Cooperates", "promises a refund date on the first call"],
  ["stall_once", "Stalls once", "won’t commit to a date on the first call, then agrees on the follow-up"],
  ["refuse_once", "Refuses once", "says no on the first call, then agrees on the follow-up"],
];

function CaseReview({ c, mode, onApprove, onFollowUp, onSetScript, onSimulateRefund }: { c: Case; mode: Mode } & Actions) {
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const done = flowIndex(c.state);
  const refunded = c.outcome === "refunded";
  const run = async (fn?: () => Promise<void>) => {
    if (!fn) return;
    setBusy(true); setErr(null);
    try { await fn(); setConfirm(false); }
    catch (e) { setErr(e instanceof Error ? e.message.split("\n")[0] : "That did not go through. Try again."); }
    finally { setBusy(false); }
  };
  const approve = () => run(onApprove && (() => onApprove(c._id)));
  const script = c.payrollScript ?? "cooperate";
  const showScript = onSetScript && !["closed", "escalate_irs", "awaiting_response", "refund_received"].includes(c.state) && (c.callAttempts ?? 0) < 2;
  const copyLetter = async () => {
    try { await navigator.clipboard.writeText(c.writtenRequest ?? ""); setCopied(true); window.setTimeout(() => setCopied(false), 2000); }
    catch { setErr("Copy did not work here; select the letter text instead."); }
  };
  const tone = refunded ? "ok" : c.state === "awaiting_approval" ? "ev" : c.state === "escalate_irs" ? "risk" : "ac";

  return (
    <section className="panel case" id="case-review">
      <div className="case-h">
        <span className="case-ic"><Icon name="cases" /></span>
        <div>
          <h2>Payroll refund review</h2>
          <p className="muted">Case {caseNo(c._id)} · {refunded ? "closed with a refund" : `next follow-up ${day(c.nextFollowUp)}`}</p>
        </div>
        <span className={`chip ${tone}`}>{refunded ? "Refunded" : stateLabel(c.state)}</span>
      </div>

      <div className="case-amt">
        <div>
          <span className="kpi-l">{refunded ? "Refunded" : "Potential refund amount"}</span>
          <span className={`big num ${refunded ? "okc" : ""}`}>{usd(c.amountCents)}</span>
        </div>
        <button type="button" className="link" onClick={() => document.getElementById("paper-trail")?.scrollIntoView({ behavior: "smooth" })}>View evidence ↗</button>
      </div>

      <ol className="flow" aria-label="Case progress">
        {FLOW.map((k, n) => (
          <li key={k} className={n < done ? "done" : n === done && !refunded ? "now" : ""}>
            <span className="bar" />
            <span className="fl num">{String(n + 1).padStart(2, "0")} · {FLOW_LABEL[k]}</span>
          </li>
        ))}
      </ol>

      {c.draft && (
        <div className="draft">
          <span className="draft-t">{c.state === "awaiting_approval" ? "Prepared for your review" : "Request approved by Priya"}</span>
          <p>{c.draft}</p>
        </div>
      )}

      {c.state === "awaiting_approval" && !confirm && (
        <div className="act">
          <button type="button" className="btn" onClick={() => setConfirm(true)}>Review &amp; approve request →</button>
          <span className="muted">Nothing has been sent</span>
        </div>
      )}
      {c.state === "awaiting_approval" && confirm && (
        <div className="confirm">
          <p><b>Approve and contact payroll?</b> Docket will call University Dining payroll about {usd(c.amountCents)}. The agent says it is an AI assistant acting with your permission, shares only this request, and never mentions the hours flag.</p>
          <div className="act">
            <button type="button" className="btn" onClick={approve} disabled={busy}>{busy ? "Approving…" : "Approve and contact payroll"}</button>
            <button type="button" className="btn ghost" onClick={() => setConfirm(false)} disabled={busy}>Not now</button>
          </div>
          {mode === "live" && <p className="note">This runs the same approval as replying YES in ASI:One.</p>}
          {err && <p className="err">{err}</p>}
        </div>
      )}
      {c.state === "contacting_employer" && (c.callError
        ? <div className="status riskc">The call could not start: {c.callError}</div>
        : <div className="status"><span className="spin" />{c.callRequestId ? "On the phone with payroll now. The call log appears here when it ends." : "Placing the call to payroll…"}</div>)}
      {c.calls.map((call, i) => (
        <div className="call" key={call._id}>
          <div className="call-h"><b>Call {c.calls.length - i} · {call.answeredBy}</b><span className="muted num">{time(call.at)}</span></div>
          <p>{call.summary}</p>
          {(call.promisedBy || call.referenceNo) && <p className="muted num">{call.promisedBy && <>Promised by {day(call.promisedBy)}. </>}{call.referenceNo && <>Ref {call.referenceNo}.</>}</p>}
        </div>
      ))}
      {c.state === "written_request" && (
        <div className="letter">
          <div className="letter-h">
            <span className="draft-t">Written request to payroll</span>
            <span className="muted">{c.writtenRequest ? "Prepared for Priya to send from her own email" : "The Caseworker is writing it…"}</span>
          </div>
          {c.writtenRequest && <p className="letter-body">{c.writtenRequest}</p>}
          {c.writtenRequest && (
            <div className="act">
              <button type="button" className="btn" onClick={() => run(onFollowUp && (() => onFollowUp(c._id)))} disabled={busy || !onFollowUp}>{busy ? "Calling…" : "Follow up by phone now"}</button>
              <button type="button" className="btn ghost" onClick={copyLetter}>{copied ? "Copied" : "Copy letter"}</button>
              <span className="muted">Scheduled follow-up: {day(c.nextFollowUp)}</span>
            </div>
          )}
          {err && <p className="err">{err}</p>}
        </div>
      )}
      {showScript && (
        <div className="script" role="group" aria-label="Rehearsal setting">
          <div className="script-h"><span className="draft-t">Rehearsal setting</span><span className="muted">What the teammate playing payroll does. It never changes what the voice agent says.</span></div>
          <div className="seg script-seg">
            {SCRIPTS.map(([k, label]) => (
              <button key={k} type="button" className={script === k ? "on" : ""} aria-pressed={script === k} onClick={() => run(() => onSetScript!(c._id, k))}>{label}</button>
            ))}
          </div>
          <p className="note">Payroll {SCRIPTS.find(([k]) => k === script)![2]}.</p>
        </div>
      )}
      {c.state === "awaiting_response" && mode === "demo" && onSimulateRefund && (
        <div className="act"><button type="button" className="btn ghost" onClick={onSimulateRefund}>Simulate the refund deposit</button><span className="muted">Stands in for two weeks passing</span></div>
      )}
      {c.state === "escalate_irs" && c.outcome && <p className="note">{c.outcome}</p>}
      {refunded && <div className="status okc">The {usd(c.amountCents)} deposit was matched to this case, and the case is closed.</div>}
      <p className="fine">You see exactly what is shared before anything is sent. Likely, not certain: confirm with your international office.</p>
    </section>
  );
}

function StubList({ stubs, selected, onSelect, limit, pinned }: { stubs: Snapshot["paystubs"]; selected: number; onSelect: (k: number) => void; limit?: number; pinned?: number }) {
  let idx = stubs.map((_, k) => k).reverse();
  if (limit) {
    idx = idx.slice(0, limit);
    if (pinned !== undefined && pinned >= 0 && !idx.includes(pinned)) idx = [...idx.slice(0, limit - 1), pinned];
  }
  if (!stubs.length) return <p className="muted pad">No paystubs yet. The Ledger reads them when Priya asks “check my pay”.</p>;
  return (
    <div className="stubs" role="list">
      <div className="stub head"><span>Document</span><span>Net pay</span><span>Withheld</span></div>
      {idx.map((k) => {
        const p = stubs[k];
        const over = p.hoursByWeek.some((h) => h > 20);
        return (
          <button key={p._id} type="button" role="listitem" className={`stub ${k === selected ? "on" : ""}`} onClick={() => onSelect(k)}>
            <span><b>Paystub {String(k + 1).padStart(2, "0")}</b><small>{day(p.periodStart)} – {day(p.periodEnd)}{over ? " · hours flag" : ""}</small></span>
            <span className="num">{usd(p.netCents)}</span>
            <span className="num evc">{usd(p.ssCents + p.medicareCents)}</span>
          </button>
        );
      })}
    </div>
  );
}

function Docket({ feed, limit }: { feed: Activity[] | undefined; limit?: number }) {
  if (feed === undefined) return <p className="muted pad">Loading…</p>;
  if (!feed.length) return <p className="muted pad">Quiet. Every agent writes an entry for each action, and for each action it decides not to take.</p>;
  // Entries are numbered in the order they were filed, like a court docket.
  const numbered = [...feed].sort((a, b) => a.at.localeCompare(b.at)).map((r, k) => ({ r, n: k + 1 })).reverse();
  const rows = limit ? numbered.slice(0, limit) : numbered;
  return (
    <ol className="docket">
      {rows.map(({ r, n }) => (
        <li key={r._id} className={`entry a-${r.agent} k-${r.action}`}>
          <span className="no num">{n}</span>
          <div>
            <div className="e-t">{actionLabel(r.action)}</div>
            <div className="e-m"><span className="ag">{AGENT_LABEL[r.agent] ?? r.agent}</span><span className="num">{time(r.at)}</span></div>
            <p className="e-d">{r.detail}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}

function DocketView({ feed }: { feed: Activity[] | undefined }) {
  const [who, setWho] = useState<string>("all");
  const agents = useMemo(() => Array.from(new Set((feed ?? []).map((r) => r.agent))), [feed]);
  const shown = (feed ?? []).filter((r) => who === "all" || r.agent === who);
  return (
    <>
      <section className="hero"><div><h1>The docket.</h1><p className="muted">Every action every agent took on Priya’s file, including the ones it decided not to take.</p></div></section>
      <div className="filters" role="group" aria-label="Filter by agent">
        {["all", ...agents].map((a) => (
          <button key={a} type="button" className={who === a ? "on" : ""} onClick={() => setWho(a)}>{a === "all" ? "All agents" : AGENT_LABEL[a] ?? a}<span className="num">{a === "all" ? feed?.length ?? 0 : feed?.filter((r) => r.agent === a).length}</span></button>
        ))}
      </div>
      <section className="panel"><Docket feed={feed === undefined ? undefined : shown} /></section>
    </>
  );
}

function PaystubsView({ snap, stubs, selected, onSelect, wide }: { snap: Snapshot; stubs: Snapshot["paystubs"]; selected: number; onSelect: (k: number) => void; wide: boolean }) {
  const weeks = stubs.flatMap((p, k) => p.hoursByWeek.map((h, w) => ({ h, k, start: new Date(new Date(p.periodStart + "T12:00:00").getTime() + 7 * w * 86400000) })));
  const W = 760, H = 170, L = 28, R = 8, T = 16, B = 26, pw = W - L - R, ph = H - T - B, max = 28, slot = pw / Math.max(1, weeks.length);
  const y = (v: number) => T + ph - (v / max) * ph;
  const tot = (f: (p: Snapshot["paystubs"][number]) => number) => usd(stubs.reduce((s, p) => s + f(p), 0));
  return (
    <>
      <section className="hero"><div><h1>Every paystub, checked.</h1><p className="muted">Transcribed by Claude, then every number recomputed in code before any rule runs.</p></div></section>
      {weeks.length > 0 && (
        <section className="panel pad">
          <div className="panel-h flat"><h2>Hours by week</h2><span className="muted">The dashed line is the 20-hour limit while school is in session</span></div>
          <svg className="hours" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Hours worked each week, with the 20-hour limit">
            <line className="g" x1={L} x2={W - R} y1={y(0)} y2={y(0)} />
            <text className="ax" x={L - 6} y={y(0) + 4} textAnchor="end">0</text>
            <text className="ax" x={L - 6} y={y(20) + 4} textAnchor="end">20</text>
            {weeks.map((w, n) => (
              <g key={n} className={`wk ${w.k === selected ? "sel" : ""}`} onClick={() => onSelect(w.k)}>
                <rect className={w.h > 20 ? "over" : ""} x={L + n * slot + slot * 0.2} y={y(w.h)} width={slot * 0.6} height={y(0) - y(w.h)} rx={2} />
                {w.h > 20 && <text className="ax risk" x={L + n * slot + slot / 2} y={y(w.h) - 6} textAnchor="middle">{w.h} h</text>}
              </g>
            ))}
            <line className="limit" x1={L} x2={W - R} y1={y(20)} y2={y(20)} />
            <text className="ax" x={L} y={H - 8}>{day(weeks[0].start.toISOString().slice(0, 10))}</text>
            <text className="ax" x={W - R} y={H - 8} textAnchor="end">{day(weeks[weeks.length - 1].start.toISOString().slice(0, 10))}</text>
          </svg>
        </section>
      )}
      <section className="panel">
        <div className="tbl">
          <table>
            <thead><tr><th>Paystub</th><th>Pay period</th><th>Hours</th><th>Gross</th><th>Social Security</th><th>Medicare</th><th>Net</th></tr></thead>
            <tbody>
              {stubs.map((p, k) => (
                <tr key={p._id} className={k === selected ? "on" : ""} onClick={() => onSelect(k)}>
                  <td><button type="button" className="link" onClick={() => onSelect(k)}>{String(k + 1).padStart(2, "0")}</button></td>
                  <td>{day(p.periodStart)} – {day(p.periodEnd)}</td>
                  <td className="num">{p.hoursByWeek.map((h, i) => <span key={i} className={h > 20 ? "riskc" : ""}>{i ? " + " : ""}{h}</span>)}</td>
                  <td className="num">{usd(p.grossCents)}</td><td className="num evc">{usd(p.ssCents)}</td><td className="num evc">{usd(p.medicareCents)}</td><td className="num">{usd(p.netCents)}</td>
                </tr>
              ))}
              {stubs.length > 0 && <tr className="total"><td>{stubs.length}</td><td>Total</td><td className="num">{stubs.reduce((s, p) => s + p.hoursByWeek.reduce((a, b) => a + b, 0), 0)}</td><td className="num">{tot((p) => p.grossCents)}</td><td className="num">{tot((p) => p.ssCents)}</td><td className="num">{tot((p) => p.medicareCents)}</td><td className="num">{tot((p) => p.netCents)}</td></tr>}
            </tbody>
          </table>
        </div>
      </section>
      {stubs[selected] && <PaperTrail snap={snap} stub={stubs[selected]} index={selected} wide={wide} />}
    </>
  );
}

const CASE_FLOW = ["open", "awaiting_approval", "contacting_employer", "awaiting_response", "refund_received", "closed"];
function CasesView({ snap, mode, ...actions }: { snap: Snapshot; mode: Mode } & Actions) {
  return (
    <>
      <section className="hero"><div><h1>Cases and flags.</h1><p className="muted">A case opens only from a flag whose quote matched the official source word for word.</p></div></section>
      <div className="cases-grid">
        <div className="col">
          {snap.cases.length === 0 && <section className="panel pad"><p className="muted">No cases yet.</p></section>}
          {snap.cases.map((c) => (
            <div key={c._id} className="col">
              <CaseReview c={c} mode={mode} {...actions} />
              <section className="panel pad">
                <h2>State machine</h2>
                <ol className="states">
                  {CASE_FLOW.map((s, n) => {
                    const at = CASE_FLOW.indexOf(c.state === "written_request" ? "contacting_employer" : c.state === "escalate_irs" ? "awaiting_response" : c.state);
                    return <li key={s} className={c.state === "closed" || n < at ? "done" : n === at ? "now" : ""}>{stateLabel(s === "awaiting_approval" ? s : s)}</li>;
                  })}
                  <li className={`branch ${c.state === "written_request" ? "now" : ""}`}>If payroll stalls or refuses on the first call: a written request, then a follow-up call</li>
                  <li className={`branch ${c.state === "escalate_irs" ? "now" : ""}`}>If payroll still won’t refund: escalate to the IRS with Forms 843 and 8316</li>
                </ol>
              </section>
            </div>
          ))}
        </div>
        <div className="col">
          {snap.flags.map((f) => (
            <section className="panel pad flag" key={f._id}>
              <div className="flag-h"><h2>{RULE_LABEL[f.ruleId] ?? f.ruleId}</h2>{f.amountCents > 0 && <span className="num big-s">{usd(f.amountCents)}</span>}</div>
              <p>{f.explanation}</p>
              <blockquote>“{f.quote}”</blockquote>
              <div className="rule-src">{f.sourceUrl ? <a href={f.sourceUrl} target="_blank" rel="noreferrer">{f.sourceTitle ?? f.sourceUrl}</a> : f.sourceTitle}</div>
              <span className={`chip ${f.status === "resolved" ? "ok" : f.ruleId === "ONCAMPUS_20_HOURS" ? "risk" : "ev"}`}>{f.status.replace(/_/g, " ")}</span>
            </section>
          ))}
        </div>
      </div>
    </>
  );
}

function Spark({ values, done }: { values: number[]; done: boolean }) {
  const max = Math.max(1, ...values);
  return (
    <svg className={`spark ${done ? "done" : ""}`} viewBox={`0 0 ${values.length * 7} 24`} aria-hidden="true">
      {values.map((v, k) => <rect key={k} x={k * 7} y={24 - (v / max) * 24} width={4.5} height={(v / max) * 24} rx={1} />)}
    </svg>
  );
}

function Loading() {
  return <div className="loading"><span className="spin" />Opening Priya’s student file…</div>;
}

function Mark() {
  return (
    <svg className="mark" viewBox="0 0 28 28" aria-hidden="true">
      <rect x="1" y="1" width="26" height="26" rx="7" className="m-bg" />
      <path d="M9 7.5h6.5a5.5 5.5 0 0 1 0 11H9z" className="m-d" />
      <path d="M8 21.5h12" className="m-l" />
    </svg>
  );
}

function Icon({ name }: { name: Tab }) {
  const d = {
    overview: "M3 3h4.5v4.5H3zM9.5 3H14v4.5H9.5zM3 9.5h4.5V14H3zM9.5 9.5H14V14H9.5z",
    paystubs: "M4 2.5h6l3 3V14H4zM10 2.5v3h3M6 8.5h5M6 11h5",
    cases: "M2.5 5h12v8.5h-12zM6 5V3.5h5V5M2.5 8.5h12",
    activity: "M2 9h3l2-5 3 9 2-4h3",
    tracks: "M3 4h11M3 8.5h11M3 13h11M5.5 2.5v3M11 7v3M7.5 11.5v3",
  }[name];
  return <svg className="ic" viewBox="0 0 17 17" aria-hidden="true"><path d={d} /></svg>;
}

const initials = (n: string) => n.split(" ").map((s) => s[0]).join("").slice(0, 2).toUpperCase();
const caseNo = (id: string) => "DKT-" + (id.startsWith("demo") ? "0042" : id.replace(/[^0-9a-z]/gi, "").slice(-4).toUpperCase());
const shortRule = (r: string) => ({ FICA_EXEMPT_F1: "Withholding", ONCAMPUS_20_HOURS: "work-hours flag", FORM_8843_ANNUAL: "Form 8843" } as Record<string, string>)[r] ?? r;
function termName(iso: string) {
  const m = Number(iso.slice(5, 7)), y = iso.slice(0, 4);
  return `${m <= 5 ? "Spring" : m <= 7 ? "Summer" : "Fall"} ${y}`;
}
