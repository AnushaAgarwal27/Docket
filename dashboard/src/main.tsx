import { Component, StrictMode } from "react";
import type { ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { ConvexProvider, ConvexReactClient } from "convex/react";
import { DemoApp, LiveApp } from "./App";
import "./styles.css";

/** A render error anywhere under here would otherwise leave a blank page, which during a demo is
 *  the worst possible failure: nothing to read and nothing to debug. Show what broke instead. */
class Boundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state: { error: Error | null } = { error: null };
  static getDerivedStateFromError(error: Error) { return { error }; }
  componentDidCatch(error: Error) { console.error("Docket dashboard failed to render:", error); }
  render() {
    if (this.state.error === null) return this.props.children;
    return (
      <div className="page" style={{ paddingTop: 48, maxWidth: 70 + "ch" }}>
        <h1 style={{ fontFamily: "var(--display)", fontSize: 28, fontWeight: 800 }}>
          The dashboard hit an error.
        </h1>
        <p className="muted" style={{ marginTop: 10 }}>
          Nothing in the student file changed. Reload to try again; the message below says what broke.
        </p>
        <pre style={{
          marginTop: 18, padding: 16, borderRadius: 12, background: "var(--panel)",
          border: "1px solid var(--line)", fontFamily: "var(--mono)", fontSize: 12,
          whiteSpace: "pre-wrap", overflowX: "auto",
        }}>{this.state.error.message}{"\n\n"}{this.state.error.stack}</pre>
      </div>
    );
  }
}

// Live when CONVEX_URL is set (repo-root .env). Add ?demo to the URL, or leave CONVEX_URL unset,
// to run the labelled synthetic demo for rehearsals and the backup video.
const url = import.meta.env.CONVEX_URL as string | undefined;
const demo = !url || new URLSearchParams(location.search).has("demo");

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Boundary>
      {demo ? (
        <DemoApp />
      ) : (
        <ConvexProvider client={new ConvexReactClient(url!)}>
          <LiveApp />
        </ConvexProvider>
      )}
    </Boundary>
  </StrictMode>,
);
