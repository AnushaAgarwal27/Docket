import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { ConvexProvider, ConvexReactClient } from "convex/react";
import { DemoApp, LiveApp } from "./App";
import "./styles.css";

// Live when CONVEX_URL is set (repo-root .env). Add ?demo to the URL, or leave CONVEX_URL unset,
// to run the labelled synthetic demo for rehearsals and the backup video.
const url = import.meta.env.CONVEX_URL as string | undefined;
const demo = !url || new URLSearchParams(location.search).has("demo");

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    {demo ? (
      <DemoApp />
    ) : (
      <ConvexProvider client={new ConvexReactClient(url!)}>
        <LiveApp />
      </ConvexProvider>
    )}
  </StrictMode>,
);
