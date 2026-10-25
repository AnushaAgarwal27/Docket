import { useState } from "react";
import type { ReactNode } from "react";
import type { Id } from "../../convex/_generated/dataModel";
import type { DocumentRow, GroupRow, NotificationRow, ResearchRow, StudentCall } from "./data";
import { day, time, usd } from "./data";

// The four surfaces added for the voice, research, filing and group layers. Each one renders from
// the same dashboard snapshot the rest of the page uses, so nothing here fetches on its own.

function Empty({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="empty">
      <strong>{title}</strong>
      {children}
    </div>
  );
}

const CHANNEL_LABEL: Record<string, string> = {
  chat: "ASI:One chat", voice: "phone call", sms: "text message", inapp: "here",
};

function ChannelIcon({ channel }: { channel: string }) {
  return (
    <span className={`chan ${channel}`} title={CHANNEL_LABEL[channel] ?? channel}>
      <svg viewBox="0 0 16 16" aria-hidden="true">
        {channel === "voice" ? (
          <path d="M3 3h3l1.5 3.5L6 8a7 7 0 0 0 2 2l1.5-1.5L13 10v3H3z" />
        ) : channel === "sms" ? (
          <path d="M2 3h12v8H7l-3 2.5V11H2z" />
        ) : (
          <path d="M2 4h12v8H2zM2 4l6 4 6-4" />
        )}
      </svg>
    </span>
  );
}

// ---------------------------------------------------------------------------
// Messages: every notification, whatever channel carried it, as one thread.
// ---------------------------------------------------------------------------

export function Messages({ rows, calls }: { rows: NotificationRow[]; calls: StudentCall[] }) {
  if (rows.length === 0 && calls.length === 0) {
    return (
      <Empty title="Nothing sent yet">
        Everything Docket tells Priya — in ASI:One, by text, or on the phone — is recorded here,
        with whether it reached her.
      </Empty>
    );
  }
  return (
    <div className="thread">
      {rows.map((n) => (
        <article key={n._id} className={`msg ${n.state === "acknowledged" ? "acknowledged" : ""} ${
          n.awaiting && n.awaiting !== "none" && n.state !== "acknowledged" ? "awaiting" : ""}`}>
          <header className="msg-h">
            <ChannelIcon channel={n.channel} />
            <span className="msg-t">{n.title}</span>
            <span className={`tag ${n.state === "acknowledged" ? "ok" : n.state === "failed" ? "risk" : ""}`}>
              {n.state}
            </span>
            {n.awaiting && n.awaiting !== "none" && n.state !== "acknowledged" && (
              <span className="tag ev">waiting on her</span>
            )}
            <span className="meta" style={{ marginLeft: "auto" }}>{time(n.at)}</span>
          </header>
          <p className="msg-b">{n.body}</p>
          {n.error && <span className="meta riskc">could not send: {n.error}</span>}
          {n.answer && <span className="meta okc">she answered: {n.answer}</span>}
        </article>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Calls: who Docket rang, who rang Docket, and what actually rang.
// ---------------------------------------------------------------------------

export function Calls({ rows, demoNumber }: { rows: StudentCall[]; demoNumber: string | null }) {
  if (rows.length === 0) {
    return (
      <Empty title="No calls yet">
        Docket calls Priya when something needs her, and she can call the same line back and ask
        anything. Both directions land here.
      </Empty>
    );
  }
  return (
    <div>
      {rows.map((c) => (
        <div key={c._id} className={`scall ${c.direction ?? "outbound"}`}>
          <span className="scall-d">
            <svg viewBox="0 0 16 16" aria-hidden="true">
              <path d="M3 3h3l1.5 3.5L6 8a7 7 0 0 0 2 2l1.5-1.5L13 10v3H3z" />
              {c.direction === "inbound" ? <path d="M13 3 9 7m0-4v4h4" /> : <path d="M9 7l4-4m0 4V3H9" />}
            </svg>
          </span>
          <div className="scall-b">
            <span className="s">{c.summary}</span>
            <span className="meta">
              {c.direction === "inbound" ? "she called Docket" : "Docket called"} ·{" "}
              {(c.purpose ?? "call").replace(/_/g, " ")} · {day(c.at)} {time(c.at)}
            </span>
            {c.toNumber && demoNumber && c.toNumber === demoNumber && (
              <span className="redirect">
                demo mode: dialled {c.toNumber} instead of the real number
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Documents: the filled form, with the record every value came from.
// ---------------------------------------------------------------------------

export function Documents({ rows, onDecide }: {
  rows: DocumentRow[];
  onDecide?: (documentId: Id<"documents">, approved: boolean) => Promise<void>;
}) {
  const [busy, setBusy] = useState<string | null>(null);
  if (rows.length === 0) {
    return (
      <Empty title="No forms filled in yet">
        Docket fills in Form 8843, the refund request, and the IRS claim forms from the student
        file. Each one waits here for Priya before anything is sent.
      </Empty>
    );
  }
  const decide = async (id: Id<"documents">, approved: boolean) => {
    if (!onDecide) return;
    setBusy(id);
    try { await onDecide(id, approved); } finally { setBusy(null); }
  };
  return (
    <div className="stack">
      {rows.map((d) => (
        <article key={d._id} className="doc">
          <header className="doc-h">
            <h3>{d.title}</h3>
            <span className="to">
              for {d.submitTo} · {d.state.replace(/_/g, " ")}
              {d.submissionRef ? ` · ${d.submissionRef}` : ""}
            </span>
          </header>
          <table className="doc-fields">
            <thead>
              <tr><th>Field</th><th>Value</th><th>Taken from</th></tr>
            </thead>
            <tbody>
              {d.fields.map((f, i) => (
                <tr key={i}>
                  <td>{f.label}</td>
                  <td className="v">{f.value}</td>
                  <td className="src">{f.source}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="doc-body">{d.body}</div>
          <footer className="doc-foot">
            <span className="note">
              {d.state === "awaiting_approval"
                ? `Nothing goes to ${d.submitTo} until Priya approves it.`
                : d.state === "submitted" && d.submitTo === "IRS"
                  ? "Signed off. Docket cannot file with the IRS, so printing and mailing this is hers to do."
                  : d.state === "submitted" ? `Sent to ${d.submitTo}.`
                  : d.state === "declined" ? "She said no. Nothing was sent."
                  : "Approved; waiting to be sent."}
            </span>
            {d.url && (
              <a className="btn ghost on-paper" href={d.url} target="_blank" rel="noreferrer">
                Open the PDF
              </a>
            )}
            {d.state === "awaiting_approval" && onDecide && (
              <>
                <button className="btn ghost on-paper" disabled={busy === d._id}
                        onClick={() => decide(d._id, false)}>Not yet</button>
                <button className="btn" disabled={busy === d._id}
                        onClick={() => decide(d._id, true)}>
                  {busy === d._id ? <span className="spin" /> : `Approve and send to ${d.submitTo}`}
                </button>
              </>
            )}
          </footer>
        </article>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Group case: how many are in, how much together, and her own decision.
// ---------------------------------------------------------------------------

export function Groups({ rows, onRespond }: {
  rows: GroupRow[];
  onRespond?: (groupId: Id<"groups">, join: boolean) => Promise<void>;
}) {
  const [busy, setBusy] = useState<string | null>(null);
  if (rows.length === 0) {
    return (
      <Empty title="No group case yet">
        When several students at one employer get the same finding, Docket opens a group case and
        asks each of them whether to join. Nobody is counted until they say yes.
      </Empty>
    );
  }
  const respond = async (id: Id<"groups">, join: boolean) => {
    if (!onRespond) return;
    setBusy(id);
    try { await onRespond(id, join); } finally { setBusy(null); }
  };
  return (
    <div className="stack">
      {rows.map(({ group, membership }) => {
        // One mark per invited student, in a stable order. No name is shown for anyone.
        const marks = Array.from({ length: Math.max(group.joinedCount, 1) }, () => "joined");
        return (
          <section key={group._id} className="group">
            <header className="group-h">
              <h3>{group.employer}</h3>
              <span className={`tag ${group.state === "closed" ? "ok" : "go"}`}>{group.state}</span>
              <span className="group-n">
                <b className="num">{usd(group.joinedCents)}</b>
                <span className="meta">from {group.joinedCount} joined</span>
              </span>
            </header>
            <div className="group-body">
              <p className="muted" style={{ fontSize: 13.5 }}>{group.summary}</p>
              <div className="heads" aria-label={`${group.joinedCount} students joined`}>
                {marks.map((_, i) => (
                  <span key={i} className={`head joined ${i === 0 && membership.state === "joined" ? "you" : ""}`}>
                    ✓
                  </span>
                ))}
                {membership.state === "invited" && <span className="head you">?</span>}
                {membership.state === "declined" && <span className="head declined you">—</span>}
              </div>
              {group.caseNote && <p className="meta">{group.caseNote}</p>}
              <div className="row-between">
                <span className="meta">
                  {membership.state === "joined"
                    ? `Priya is in, for ${usd(membership.amountCents)}. Her own case is unaffected.`
                    : membership.state === "declined"
                      ? "Priya chose not to join. Her own case is unaffected."
                      : "Priya has not answered yet. Her amount is not in the total above."}
                </span>
                {membership.state === "invited" && onRespond && (
                  <span style={{ display: "flex", gap: 8 }}>
                    <button className="btn ghost" disabled={busy === group._id}
                            onClick={() => respond(group._id, false)}>No thanks</button>
                    <button className="btn" disabled={busy === group._id}
                            onClick={() => respond(group._id, true)}>
                      {busy === group._id ? <span className="spin" /> : "Join the group"}
                    </button>
                  </span>
                )}
              </div>
            </div>
          </section>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Research: what Athena found, and which sources survived the check.
// ---------------------------------------------------------------------------

export function Research({ rows }: { rows: ResearchRow[] }) {
  if (rows.length === 0) {
    return (
      <Empty title="Nothing researched yet">
        Ask Docket anything on the phone or in chat and the research agent answers it here, with
        every source fetched and checked in code before it counts.
      </Empty>
    );
  }
  return (
    <div className="stack">
      {rows.map((r) => (
        <article key={r._id} className={`find ${r.confidence === "low" ? "low" : ""}`}>
          <div className="msg-h">
            <h4>{r.topic}</h4>
            <span className={`tag ${r.confidence === "high" ? "ok" : r.confidence === "low" ? "risk" : "ev"}`}>
              {r.confidence} confidence
            </span>
            <span className="tag">{r.kind === "ask" ? "she asked" : "found on watch"}</span>
            <span className="meta" style={{ marginLeft: "auto" }}>{r.engine} · {day(r.createdAt)}</span>
          </div>
          {r.question && <p className="meta">“{r.question}”</p>}
          <p>{r.answer}</p>
          {r.sources.length > 0 ? (
            <div className="find-src">
              <span className="meta">
                {r.sources.length} source{r.sources.length === 1 ? "" : "s"} fetched and checked:
              </span>
              {r.sources.map((s, i) => (
                <span key={i}>
                  <a href={s.url} target="_blank" rel="noreferrer">{s.title}</a>
                  {s.excerpt && <span className="ex">matched on the page: “{s.excerpt}”</span>}
                </span>
              ))}
            </div>
          ) : (
            <span className="meta riskc">
              No source survived the check, so this is not stated as fact.
            </span>
          )}
        </article>
      ))}
    </div>
  );
}
