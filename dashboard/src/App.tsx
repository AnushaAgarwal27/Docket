import { useQuery } from "convex/react";
import { api } from "../../convex/_generated/api";
import type { Id } from "../../convex/_generated/dataModel";

// The live dashboard: every row the agents write to the shared student file shows up here.
const STATES = ["open", "awaiting_approval", "contacting_employer", "awaiting_response", "refund_received", "closed"];
const STATE_LABEL: Record<string, string> = {
  open: "Opened",
  awaiting_approval: "Awaiting approval",
  contacting_employer: "Contacting payroll",
  awaiting_response: "Awaiting refund",
  refund_received: "Refund received",
  closed: "Closed",
  escalate_irs: "Escalated to IRS",
};
const RULE_LABEL: Record<string, string> = {
  FICA_EXEMPT_F1: "Social Security & Medicare withheld",
  ONCAMPUS_20_HOURS: "Over 20 hours in a week",
  FORM_8843_ANNUAL: "Form 8843 due",
};

const usd = (cents: number) =>
  (cents / 100).toLocaleString("en-US", { style: "currency", currency: "USD" });
const time = (iso: string) =>
  new Date(iso).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", second: "2-digit" });

export function App() {
  const profiles = useQuery(api.profiles.list);
  const profileId = profiles?.[0]?._id;
  return (
    <div className="page">
      <header className="top">
        <div className="brand">
          <span className="logo">D</span>
          <span>Docket</span>
        </div>
        <span className="live"><span className="dot" />Live</span>
      </header>
      {profiles === undefined ? (
        <p className="muted">Loading…</p>
      ) : profileId === undefined ? (
        <p className="muted">No student yet. Run <code>python -m seed.reset</code>.</p>
      ) : (
        <Student profileId={profileId} />
      )}
    </div>
  );
}

function Student({ profileId }: { profileId: Id<"profiles"> }) {
  const data = useQuery(api.dashboard.snapshot, { profileId });
  if (data === undefined) return <p className="muted">Loading…</p>;
  if (data === null) return <p className="muted">Student not found.</p>;
  const { profile, flags, cases, paystubs, transactions } = data;

  const withheld = paystubs.reduce((s, p) => s + p.ssCents + p.medicareCents, 0);
  const gross = paystubs.reduce((s, p) => s + p.grossCents, 0);
  const refunded = cases.filter((c) => c.outcome === "refunded").reduce((s, c) => s + c.amountCents, 0);
  const openCases = cases.filter((c) => c.state !== "closed").length;

  return (
    <>
      <section className="profile">
        <div>
          <h1>{profile.name}</h1>
          <p className="muted">
            {profile.visa} · {profile.school} · from {profile.homeCountry} · arrived {profile.arrivalDate}
          </p>
        </div>
        <span className="chip">{profile.workAuth}</span>
      </section>

      <section className="tiles">
        <Tile label="Paystubs read" value={String(paystubs.length)} sub={`${usd(gross)} gross`} />
        <Tile label="Withheld in error" value={usd(withheld)} sub="Social Security + Medicare" accent="warn" />
        <Tile label="Open cases" value={String(openCases)} sub={`${flags.length} flags`} />
        <Tile label="Recovered" value={usd(refunded)} sub="refund deposits matched" accent="good" />
      </section>

      <div className="grid">
        <div className="col">
          <h2>Flags</h2>
          {flags.length === 0 && <p className="empty">No flags yet. Say “check my pay” in ASI:One.</p>}
          {flags.map((f) => (
            <article className="card" key={f._id}>
              <div className="row">
                <h3>{RULE_LABEL[f.ruleId] ?? f.ruleId}</h3>
                {f.amountCents > 0 && <span className="amount">{usd(f.amountCents)}</span>}
              </div>
              <p>{f.explanation}</p>
              <blockquote>
                “{f.quote}”
                {f.sourceUrl && (
                  <a href={f.sourceUrl} target="_blank" rel="noreferrer">{f.sourceTitle ?? f.sourceUrl}</a>
                )}
              </blockquote>
              <span className={`status s-${f.status}`}>{f.status.replace(/_/g, " ")}</span>
            </article>
          ))}

          <h2>Cases</h2>
          {cases.length === 0 && <p className="empty">No cases open.</p>}
          {cases.map((c) => (
            <article className="card" key={c._id}>
              <div className="row">
                <h3>Refund case</h3>
                <span className="amount">{usd(c.amountCents)}</span>
              </div>
              <Stepper state={c.state} />
              <p className="muted small">Next follow-up {c.nextFollowUp}</p>
              {c.state === "escalate_irs" && c.outcome && <p className="note">{c.outcome}</p>}
              {c.calls.map((call) => (
                <div className="call" key={call._id}>
                  <div className="row">
                    <strong>Call · {call.answeredBy}</strong>
                    <span className="muted small">{time(call.at)}</span>
                  </div>
                  <p>{call.summary}</p>
                  <p className="muted small">
                    {call.promisedBy && <>Promised by {call.promisedBy}. </>}
                    {call.referenceNo && <>Ref {call.referenceNo}. </>}
                    {call.transcriptUrl && <a href={call.transcriptUrl} target="_blank" rel="noreferrer">Transcript</a>}
                  </p>
                </div>
              ))}
              {c.draft && (
                <details>
                  <summary>Request sent to payroll</summary>
                  <pre>{c.draft}</pre>
                </details>
              )}
            </article>
          ))}

          <h2>Money</h2>
          {transactions.length === 0 ? (
            <p className="empty">No bank activity yet. The Ledger fills this from Nessie.</p>
          ) : (
            <table>
              <tbody>
                {transactions.map((t) => (
                  <tr key={t._id}>
                    <td className="muted">{t.date}</td>
                    <td>{t.counterparty}</td>
                    <td className={t.amountCents >= 0 ? "pos" : "neg"}>{usd(t.amountCents)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <aside className="col">
          <h2>Activity</h2>
          <Feed />
        </aside>
      </div>
    </>
  );
}

function Tile({ label, value, sub, accent }: { label: string; value: string; sub: string; accent?: "warn" | "good" }) {
  return (
    <div className={`tile ${accent ?? ""}`}>
      <span className="label">{label}</span>
      <span className="value">{value}</span>
      <span className="muted small">{sub}</span>
    </div>
  );
}

function Stepper({ state }: { state: string }) {
  if (state === "escalate_irs") return <span className="status s-escalate_irs">Escalated to IRS</span>;
  const at = STATES.indexOf(state);
  return (
    <ol className="stepper">
      {STATES.slice(1).map((s, i) => (
        <li key={s} className={i + 1 < at ? "done" : i + 1 === at ? "now" : ""}>
          {STATE_LABEL[s]}
        </li>
      ))}
    </ol>
  );
}

function Feed() {
  const rows = useQuery(api.activity.recent, { limit: 60 });
  if (rows === undefined) return <p className="muted">Loading…</p>;
  if (rows.length === 0) return <p className="empty">Quiet. Agents write here on every action.</p>;
  return (
    <ul className="feed">
      {rows.map((r) => (
        <li key={r._id}>
          <div className="row">
            <span className={`agent a-${r.agent}`}>{r.agent}</span>
            <span className="muted small mono">{time(r.at)}</span>
          </div>
          <span className="action mono">{r.action}</span>
          <p>{r.detail}</p>
        </li>
      ))}
    </ul>
  );
}
