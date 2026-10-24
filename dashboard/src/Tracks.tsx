import type { Activity, Patterns, Snapshot } from "./data";
import { actionLabel, time } from "./data";
import { Suspense, lazy } from "react";

// three.js is large, so the 3D view loads only when this tab opens.
const Constellation = lazy(() => import("./Constellation").then((m) => ({ default: m.Constellation })));

// The booth view: how the agents connect, and what each sponsor's tool does in Docket, with live
// numbers from the same Convex rows the rest of the dashboard reads. Nothing here is typed in.

type Tab = "overview" | "paystubs" | "cases" | "activity" | "tracks";
const AGENTS = [
  { id: "coordinator", name: "Coordinator", role: "Talks to Priya in ASI:One; asks the other agents with typed messages" },
  { id: "ledger", name: "Ledger", role: "Bank rows from Nessie; paystub PDFs read by Claude, checked in code" },
  { id: "tax", name: "Rules", role: "Runs rules.yaml in code; a flag needs a word-for-word quote" },
  { id: "caseworker", name: "Caseworker", role: "Opens the case, places the call, writes the letter" },
] as const;

export function TracksView({ snap, feed, patterns, mode, onTab }: {
  snap: Snapshot; feed: Activity[] | undefined; patterns?: Patterns; mode: "live" | "demo"; onTab: (t: Tab) => void;
}) {
  const rows = feed ?? [];
  const count = (pred: (a: Activity) => boolean) => rows.filter(pred).length;
  const byAction = (action: string) => count((a) => a.action === action);
  const last = (agent: string) => rows.find((a) => a.agent === agent); // feed is newest first
  const agentActions = count((a) => AGENTS.some((g) => g.id === a.agent));
  const calls = snap.cases.reduce((s, c) => s + c.calls.length, 0);
  const rehearsalCalls = count((a) => a.action === "call_placed" && a.detail.startsWith("Rehearsal"));
  const placed = byAction("call_placed");
  const letters = snap.cases.filter((c) => c.writtenRequest).length;
  const linked = snap.paystubs.filter((p) => p.depositId).length;
  const cohort = patterns ? patterns.employers.reduce((s, r) => s + r.students, 0) : 0;
  const voice = last("voice");

  const TRACKS = [
    {
      name: "Fetch.ai", what: "Four uAgents. Priya talks only to the Coordinator, in ASI:One, over the chat protocol. It asks the Rules and Caseworker agents with typed messages (RunRules, OpenCases, CaseDecision), and the Ledger runs on its own interval. Every agent writes to the shared file, and the next one reacts.",
      stats: [[String(AGENTS.length), "agents"], [String(agentActions), "actions logged by agents"], [String(count((a) => a.agent === "coordinator")), "Coordinator actions"]],
      check: "Open docket-coordinator in ASI:One and say “check my pay”.", tab: "activity" as Tab, show: "See every agent action",
    },
    {
      name: "Anthropic · Claude", what: "Claude reads each paystub PDF and copies the printed values; code recomputes every number. In chat, Claude reads Priya’s message and writes the reply, and code checks every dollar amount and quote before it is shown. Rules and math never come from the model.",
      stats: [[String(snap.paystubs.length), "paystubs transcribed"], [String(snap.flags.length), "flags with a verified quote"], [String(byAction("quote_rejected")), "quotes rejected"]],
      check: "The receipt shows each flag beside the exact stored clause.", tab: "overview" as Tab, show: "See the receipt",
    },
    {
      name: "Cartesia", what: "After Priya approves, a Managed Agent calls payroll. It says it is an AI assistant, reads the case from a webhook tool, and logs the outcome through another. A stall or refusal turns into a written request and a follow-up call; it never mentions the hours flag.",
      stats: [[String(placed), rehearsalCalls ? `calls placed (${rehearsalCalls} rehearsal)` : "calls placed"], [String(calls), "outcomes logged"], [String(letters), "written requests"]],
      check: "Approve the case and the payroll phone rings.", tab: "cases" as Tab, show: "See the case and calls",
    },
    {
      name: "Convex", what: "The shared student file. Every agent reads and writes it, and every panel on this dashboard is a live query. The case state machine runs in Convex mutations, and the voice agent’s webhook tools are Convex HTTP actions.",
      stats: [[String(snap.paystubs.length + snap.transactions.length + snap.flags.length + snap.cases.length), "rows in Priya’s file"], [String(rows.length), "activity rows (latest 400)"], [String(cohort), "students in the employer view"]],
      check: "Approve on this page and watch every panel update without a refresh.", tab: "activity" as Tab, show: "See the live feed",
    },
    {
      name: "Capital One Nessie", what: "Priya’s bank. The Ledger syncs her deposits and purchases, matches each paystub to the deposit of exactly its net pay, and closes the case when the $440.64 refund deposit lands.",
      stats: [[String(snap.transactions.length), "bank rows synced"], [`${linked} of ${snap.paystubs.length}`, "paystubs matched to a deposit"], [byAction("refund_matched") ? "Yes" : "No", "refund matched yet"]],
      check: "“Simulate 2 weeks” drops the refund into Nessie; the case closes.", tab: "paystubs" as Tab, show: "See paystubs and deposits",
    },
  ];

  return (
    <>
      <section className="hero">
        <div>
          <h1>One student file. Every agent connected.</h1>
          <p className="muted">How Docket uses each sponsor’s tool, with live numbers from Priya’s file{mode === "demo" ? " (demo data)" : ""}.</p>
        </div>
      </section>

      <Suspense fallback={<section className="panel constellation"><div className="cs-stage" /></section>}>
        <Constellation feed={feed} />
      </Suspense>

      <section className="panel pad flowmap" aria-label="How the agents connect">
        <div className="fm-col">
          <span className="label">Inputs</span>
          <div className="fm-node ext"><b>ASI:One</b><span>Priya chats with Docket</span></div>
          <div className="fm-node ext"><b>Capital One Nessie</b><span>Her bank account</span></div>
          <div className="fm-node ext"><b>Paystub PDFs</b><span>Read by Claude</span></div>
        </div>
        <div className="fm-arrow" aria-hidden="true"><span>chat protocol</span><span>typed messages</span></div>
        <div className="fm-col agents">
          <span className="label">Fetch.ai uAgents</span>
          {AGENTS.map((g) => {
            const l = last(g.id);
            return (
              <div key={g.id} className={`fm-node agent ${l ? "on" : ""}`}>
                <b>{g.name}</b><span>{g.role}</span>
                <em className="num">{l ? `${actionLabel(l.action)} · ${time(l.at)}` : "No actions yet"}</em>
              </div>
            );
          })}
        </div>
        <div className="fm-arrow" aria-hidden="true"><span>with approval</span></div>
        <div className="fm-col">
          <span className="label">Actions</span>
          <div className={`fm-node ext ${voice ? "on" : ""}`}><b>Cartesia voice agent</b><span>Calls payroll; webhook tools on Convex</span><em className="num">{voice ? `${actionLabel(voice.action)} · ${time(voice.at)}` : "No calls yet"}</em></div>
          <div className="fm-node ext"><b>Written request</b><span>Prepared for Priya to send</span><em className="num">{letters ? `${letters} prepared` : "Only after a stall or refusal"}</em></div>
          <div className="fm-node ext"><b>This dashboard</b><span>Live queries, no refresh</span></div>
        </div>
        <div className="fm-base">
          <b>Convex · the shared student file</b>
          <span className="num">{snap.paystubs.length} paystubs · {snap.transactions.length} bank rows · {snap.flags.length} flags · {snap.cases.length} case · {calls} calls · {rows.length} activity rows</span>
        </div>
      </section>

      <div className="tracks">
        {TRACKS.map((t, i) => (
          <section key={t.name} className={`panel track ${i === 0 ? "lead" : ""}`}>
            <h2>{t.name}</h2>
            <p className="tr-what">{t.what}</p>
            <div className="tr-stats">
              {t.stats.map(([v, l]) => <div key={l}><b className="num">{v}</b><span>{l}</span></div>)}
            </div>
            <p className="tr-check"><span>Try it:</span> {t.check}</p>
            <button type="button" className="link" onClick={() => onTab(t.tab)}>{t.show} →</button>
          </section>
        ))}
      </div>
      <p className="fine">Counts come from the student file and the latest 400 activity rows. {rehearsalCalls ? "Rehearsal calls are simulated and place no phone call. " : ""}The employer view includes simulated students.</p>
    </>
  );
}
