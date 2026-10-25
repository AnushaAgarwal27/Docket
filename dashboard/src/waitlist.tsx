import { StrictMode, useState } from "react";
import type { FormEvent } from "react";
import { createRoot } from "react-dom/client";
import { ConvexProvider, ConvexReactClient, useMutation, useQuery } from "convex/react";
import { api } from "../../convex/_generated/api";

// The public waitlist page: name and email (required), school and visa (optional), saved to Convex.

const CSS = `
:root { --bg: #f7f7f5; --card: #ffffff; --ink: #16181d; --muted: #646a73; --line: #e2e4e8; --accent: #2f5bea; --ok: #15803d; --err: #b42318; }
@media (prefers-color-scheme: dark) { :root { --bg: #0f1115; --card: #171a21; --ink: #e8eaed; --muted: #9aa0a6; --line: #2a2f39; --accent: #7b9bff; --ok: #4ade80; --err: #f97066; } }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink); font: 16px/1.5 Inter, system-ui, -apple-system, sans-serif; }
main { max-width: 440px; margin: 0 auto; padding: 48px 16px; }
.card { background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 28px 24px; }
h1 { font-size: 26px; margin: 0 0 8px; }
p { margin: 0 0 18px; color: var(--muted); }
label { display: block; font-weight: 600; font-size: 14px; margin: 14px 0 6px; }
label span { font-weight: 400; color: var(--muted); }
input, select { width: 100%; padding: 11px 12px; border: 1px solid var(--line); border-radius: 9px; background: var(--bg); color: var(--ink); font: inherit; }
input:focus, select:focus { outline: 2px solid var(--accent); outline-offset: 1px; }
button { width: 100%; margin-top: 22px; padding: 12px; border: 0; border-radius: 9px; background: var(--accent); color: #fff; font: inherit; font-weight: 600; cursor: pointer; }
button:disabled { opacity: 0.6; cursor: default; }
.error { color: var(--err); font-size: 14px; margin-top: 12px; }
.done { color: var(--ok); font-weight: 600; font-size: 18px; margin: 0; }
.count { text-align: center; font-size: 14px; color: var(--muted); margin-top: 16px; }
`;

type Visa = "F-1" | "J-1" | "Neither";

function Waitlist() {
  const join = useMutation(api.waitlist.join);
  const count = useQuery(api.waitlist.count);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [school, setSchool] = useState("");
  const [visa, setVisa] = useState<Visa | "">("");
  const [state, setState] = useState<"idle" | "saving" | "done" | "again">("idle");
  const [error, setError] = useState("");

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setState("saving");
    try {
      const r = await join({ name, email, school: school || undefined, visa: visa || undefined });
      setState(r.alreadyJoined ? "again" : "done");
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg.match(/Please enter[^.]*\./)?.[0] ?? "Something went wrong. Please try again.");
      setState("idle");
    }
  }

  return (
    <main>
      <div className="card">
        <h1>Join the Docket waitlist</h1>
        <p>Docket checks international students' paychecks for tax taken by mistake, shows the official rule
          behind every finding, and helps get the money back. We'll email you when it's ready.</p>
        {state === "done" || state === "again" ? (
          <p className="done">{state === "done" ? "You're on the list! We'll be in touch." : "You're already on the list. We updated your details."}</p>
        ) : (
          <form onSubmit={submit}>
            <label htmlFor="name">Name</label>
            <input id="name" value={name} onChange={(e) => setName(e.target.value)} required autoComplete="name" />
            <label htmlFor="email">Email</label>
            <input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" />
            <label htmlFor="school">School <span>(optional)</span></label>
            <input id="school" value={school} onChange={(e) => setSchool(e.target.value)} />
            <label htmlFor="visa">Visa <span>(optional)</span></label>
            <select id="visa" value={visa} onChange={(e) => setVisa(e.target.value as Visa | "")}>
              <option value="">Prefer not to say</option>
              <option value="F-1">F-1</option>
              <option value="J-1">J-1</option>
              <option value="Neither">Neither</option>
            </select>
            <button type="submit" disabled={state === "saving"}>{state === "saving" ? "Joining…" : "Join the waitlist"}</button>
            {error && <div className="error">{error}</div>}
          </form>
        )}
      </div>
      {count !== undefined && count > 0 && <div className="count">{count} {count === 1 ? "person has" : "people have"} joined</div>}
    </main>
  );
}

const style = document.createElement("style");
style.textContent = CSS;
document.head.appendChild(style);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ConvexProvider client={new ConvexReactClient(import.meta.env.CONVEX_URL as string)}>
      <Waitlist />
    </ConvexProvider>
  </StrictMode>,
);
