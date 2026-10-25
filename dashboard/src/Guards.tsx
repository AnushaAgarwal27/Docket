import { Component, Suspense } from "react";
import type { ReactNode } from "react";

// Two boundaries the dashboard needs so that one broken piece does not take the page with it.

/** An optional panel: if it throws, render `fallback` (nothing, by default) and carry on.
 *  Used for panels whose backend function may not be deployed yet. */
export class Guard extends Component<{ children: ReactNode; fallback?: ReactNode; what?: string },
                                     { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch(e: Error) {
    console.warn(`${this.props.what ?? "Optional panel"} unavailable:`, e.message);
  }
  render() { return this.state.failed ? (this.props.fallback ?? null) : this.props.children; }
}

/** A 3D panel. These need a WebGL context, and some machines will not give them one: an old GPU, a
 *  locked-down browser, a remote desktop, a headless run. three.js throws when that happens, and an
 *  unguarded throw during the demo would take the whole page down over a decoration. Everything the
 *  3D shows is also on the page as text, so losing it costs the look and nothing else. */
export function Stage({ children, fallback }: { children: ReactNode; fallback: ReactNode }) {
  return (
    <Guard what="3D view" fallback={fallback}>
      <Suspense fallback={fallback}>{children}</Suspense>
    </Guard>
  );
}
