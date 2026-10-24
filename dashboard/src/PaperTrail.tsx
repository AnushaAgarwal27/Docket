import { useLayoutEffect, useRef, useState } from "react";
import type { Flag, Paystub, Snapshot } from "./data";
import { MEDICARE_BP, SS_BP, calendarYear, day, pct, usd } from "./data";

// The paper trail: every highlighted line on the paystub is threaded to the arithmetic that
// checked it in code, and on to the exact clause that makes it a problem. Hover any piece to
// light up its thread.

type Link = { from: string; to: string; key: string };
const LINKS: Link[] = [
  { from: "doc-ss", to: "calc-ss", key: "ss" },
  { from: "doc-med", to: "calc-med", key: "med" },
  { from: "calc-ss", to: "rule-fica", key: "ss" },
  { from: "calc-med", to: "rule-fica", key: "med" },
  { from: "calc-year", to: "rule-fica", key: "year" },
  { from: "doc-hours", to: "calc-hours", key: "hours" },
  { from: "calc-hours", to: "rule-hours", key: "hours" },
];
type Thread = { d: string; key: string; x1: number; y1: number; x2: number; y2: number };

export function PaperTrail(props: {
  snap: Snapshot;
  stub: Paystub;
  index: number;
  wide: boolean;
}) {
  const { snap, stub, index, wide } = props;
  const { profile, flags, transactions } = snap;
  const box = useRef<HTMLDivElement>(null);
  const [threads, setThreads] = useState<Thread[]>([]);
  const [hover, setHover] = useState<string | null>(null);
  const [pane, setPane] = useState<"doc" | "calc" | "rule">("doc");

  const fica = flags.find((f) => f.ruleId === "FICA_EXEMPT_F1");
  const hoursFlag = flags.find((f) => f.ruleId === "ONCAMPUS_20_HOURS");
  const overWeek = stub.hoursByWeek.findIndex((h) => h > 20);
  const year = calendarYear(profile.arrivalDate, Number(stub.periodStart.slice(0, 4)));
  const ssExpected = pct(stub.grossCents, SS_BP);
  const medExpected = pct(stub.grossCents, MEDICARE_BP);
  const weekStart = (k: number) => new Date(new Date(stub.periodStart + "T12:00:00").getTime() + 7 * k * 86400000).toISOString().slice(0, 10);
  const deposit = transactions.find((t) => {
    if (t.kind !== "deposit" || t.amountCents !== stub.netCents) return false;
    const gap = (new Date(t.date + "T12:00:00").getTime() - new Date(stub.periodEnd + "T12:00:00").getTime()) / 86400000;
    return gap >= 0 && gap <= 3;
  });
  const num = String(index + 1).padStart(2, "0");

  useLayoutEffect(() => {
    const el = box.current;
    if (!el || !wide) { setThreads([]); return; }
    const draw = () => {
      const base = el.getBoundingClientRect();
      const find = (name: string) => el.querySelector<HTMLElement>(`[data-anchor="${name}"]`);
      const out: Thread[] = [];
      for (const l of LINKS) {
        const a = find(l.from), b = find(l.to);
        if (!a || !b) continue;
        const ra = a.getBoundingClientRect(), rb = b.getBoundingClientRect();
        const x1 = ra.right - base.left, y1 = ra.top + ra.height / 2 - base.top;
        const x2 = rb.left - base.left, y2 = l.to.startsWith("rule") ? rb.top + 28 - base.top : rb.top + rb.height / 2 - base.top;
        const dx = Math.max(24, (x2 - x1) * 0.55);
        out.push({ d: `M${x1},${y1} C${x1 + dx},${y1} ${x2 - dx},${y2} ${x2},${y2}`, key: l.key, x1, y1, x2, y2 });
      }
      setThreads(out);
    };
    draw();
    const ro = new ResizeObserver(draw);
    ro.observe(el);
    document.fonts?.ready.then(draw);
    return () => ro.disconnect();
  }, [wide, stub._id, flags.length]);

  const lit = (k: string) => (hover === k ? "lit" : hover ? "dim" : "");
  const hov = (k: string) => ({ onMouseEnter: () => setHover(k), onMouseLeave: () => setHover(null), onFocus: () => setHover(k), onBlur: () => setHover(null), tabIndex: 0 });

  return (
    <section className="panel trail" id="paper-trail" aria-label="Paper trail">
      <div className="panel-h">
        <div>
          <h2>Paper trail</h2>
          <p className="muted">Paystub {num}: every highlighted line traced to the math and the rule behind it.</p>
        </div>
        <span className="chip ev">Paystub {num}</span>
      </div>

      {!wide && (
        <div className="seg" role="tablist" aria-label="Evidence view">
          {([["doc", "Document"], ["calc", "Calculation"], ["rule", "Rule review"]] as const).map(([k, label]) => (
            <button key={k} role="tab" aria-selected={pane === k} className={pane === k ? "on" : ""} onClick={() => setPane(k)} type="button">{label}</button>
          ))}
        </div>
      )}

      <div className={`trail-grid ${wide ? "wide" : ""}`} ref={box}>
        {wide && (
          <svg className="threads" aria-hidden="true">
            {threads.map((t, k) => (
              <g key={k} className={`thread t-${t.key} ${lit(t.key)}`}>
                <path d={t.d} />
                <circle cx={t.x1} cy={t.y1} r={3.5} />
                <circle cx={t.x2} cy={t.y2} r={3.5} />
              </g>
            ))}
          </svg>
        )}

        {(wide || pane === "doc") && (
          <div className="paper" aria-label={`Paystub ${num}, synthetic`}>
            <div className="paper-top">
              <div>
                <div className="paper-org">{stub.employer}</div>
                <div className="paper-sub">{profile.school}</div>
              </div>
              <div className="paper-r">
                <div className="paper-org">Earnings statement</div>
                <div className="paper-sub">No. {num} of {snap.paystubs.length}</div>
              </div>
            </div>
            <dl className="paper-meta">
              <div><dt>Employee</dt><dd>{profile.name} · synthetic</dd></div>
              <div><dt>Pay period</dt><dd>{day(stub.periodStart)} – {day(stub.periodEnd)}, {stub.periodEnd.slice(0, 4)}</dd></div>
            </dl>
            <div className="paper-lines">
              {stub.hoursByWeek.map((h, k) => (
                <div key={k} className={`pl ${k === overWeek ? `hl risk ${lit("hours")}` : ""}`} data-anchor={k === overWeek ? "doc-hours" : undefined} {...(k === overWeek ? hov("hours") : {})}>
                  <span>Hours, week of {day(weekStart(k))}</span><span className="num">{h.toFixed(2)}</span>
                </div>
              ))}
              <div className="pl"><span>Rate</span><span className="num">$18.00 / hour</span></div>
              <div className="pl strong"><span>Gross pay</span><span className="num">{usd(stub.grossCents)}</span></div>
              <div className={`pl hl ${lit("ss")}`} data-anchor="doc-ss" {...hov("ss")}><span>Social Security</span><span className="num">−{usd(stub.ssCents)}</span></div>
              <div className={`pl hl ${lit("med")}`} data-anchor="doc-med" {...hov("med")}><span>Medicare</span><span className="num">−{usd(stub.medicareCents)}</span></div>
              <div className="pl"><span>Federal income tax</span><span className="num">{usd(stub.grossCents - stub.ssCents - stub.medicareCents - stub.netCents)}</span></div>
              <div className="pl strong total"><span>Net pay</span><span className="num">{usd(stub.netCents)}</span></div>
            </div>
            <p className="paper-foot">
              {deposit ? <>Deposited {day(deposit.date)} · {deposit.counterparty} · matched</> : <>No matching deposit yet</>}
              <br />{stub.sourceFile} · transcribed by Claude, every number checked in code
            </p>
          </div>
        )}

        {wide && <div className="gutter" />}

        {(wide || pane === "calc") && (
          <div className="calc">
            <span className="label">Checked in code</span>
            <div className={`ci ${lit("ss")}`} data-anchor="calc-ss" {...hov("ss")}>
              <span className="ci-t">Social Security</span>
              <span className="ci-m num">6.20% × {usd(stub.grossCents)} = {usd(ssExpected)}</span>
              <span className="ci-r">{stub.ssCents === ssExpected ? <><b className="okc">Matches</b> the {usd(stub.ssCents)} withheld</> : <b className="riskc">Off by {usd(Math.abs(stub.ssCents - ssExpected))}</b>}</span>
            </div>
            <div className={`ci ${lit("med")}`} data-anchor="calc-med" {...hov("med")}>
              <span className="ci-t">Medicare</span>
              <span className="ci-m num">1.45% × {usd(stub.grossCents)} = {usd(medExpected)}</span>
              <span className="ci-r">{stub.medicareCents === medExpected ? <><b className="okc">Matches</b> the {usd(stub.medicareCents)} withheld</> : <b className="riskc">Off by {usd(Math.abs(stub.medicareCents - medExpected))}</b>}</span>
            </div>
            <div className={`ci ${lit("year")}`} data-anchor="calc-year" {...hov("year")}>
              <span className="ci-t">Calendar year on F-1</span>
              <span className="ci-m num">{stub.periodStart.slice(0, 4)} − {profile.arrivalDate.slice(0, 4)} + 1 = year {year} of 5</span>
              <span className="ci-r">{year <= 5 ? <>Inside the exempt window, so both should be <b className="evc">$0.00</b></> : <>Past the window; withholding is expected</>}</span>
            </div>
            {overWeek >= 0 && (
              <div className={`ci risk ${lit("hours")}`} data-anchor="calc-hours" {...hov("hours")}>
                <span className="ci-t">Hours, week of {day(weekStart(overWeek))}</span>
                <span className="ci-m num">{stub.hoursByWeek[overWeek]} − 20 limit = {stub.hoursByWeek[overWeek] - 20} over</span>
                <span className="ci-r">School was in session, so the limit applies</span>
              </div>
            )}
          </div>
        )}

        {wide && <div className="gutter" />}

        {(wide || pane === "rule") && (
          <div className="rules">
            <span className="label">The rule it relies on</span>
            {fica ? <RuleCard anchor="rule-fica" flag={fica} cls={lit("ss") || lit("med") || lit("year")} onHover={setHover} keyName="ss" /> : <p className="muted">No rule has flagged this paystub yet.</p>}
            {overWeek >= 0 && hoursFlag && <RuleCard anchor="rule-hours" flag={hoursFlag} cls={lit("hours")} onHover={setHover} keyName="hours" risk />}
          </div>
        )}
      </div>
    </section>
  );
}

function RuleCard({ anchor, flag, cls, onHover, keyName, risk }: { anchor: string; flag: Flag; cls: string; onHover: (k: string | null) => void; keyName: string; risk?: boolean }) {
  return (
    <article className={`rule ${risk ? "risk" : ""} ${cls}`} data-anchor={anchor} onMouseEnter={() => onHover(keyName)} onMouseLeave={() => onHover(null)}>
      <blockquote>“{flag.quote}”</blockquote>
      <div className="rule-src">
        {flag.sourceUrl ? <a href={flag.sourceUrl} target="_blank" rel="noreferrer">{flag.sourceTitle ?? flag.sourceUrl}</a> : <span>{flag.sourceTitle}</span>}
      </div>
      <div className="rule-foot">
        <span className="chip ok">Quote verified word for word</span>
        <span className="muted">Likely, not certain. Confirm with your international office.</span>
      </div>
    </article>
  );
}
