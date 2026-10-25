import { execFile } from "node:child_process";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { defineConfig, loadEnv, type Plugin } from "vite";
import react from "@vitejs/plugin-react";

const ROOT = resolve(__dirname, "..");
const GAME = resolve(ROOT, "docket-game.html");

// The Hearing game lives at the repo root (docket-game.html) and stays a standalone page.
// Served here as /game.html with the Convex URL filled in, so its live case reads the same
// student file as the dashboard. In dev, POST /__docket/release-refund posts the refund to the
// Nessie test account (seed/release_refund.py), the "fast-forward" the game offers; the Nessie key
// stays on this machine. A built site has no such endpoint and the game says how to run it instead.
function hearingGame(convexUrl: string | undefined): Plugin {
  const page = () => {
    const html = readFileSync(GAME, "utf8");
    return convexUrl
      ? html.replace("<head>", `<head>\n<meta name="convex-url" content="${convexUrl}">`)
      : html;
  };
  return {
    name: "docket-hearing-game",
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const path = (req.url ?? "").split("?")[0];
        if (req.method === "GET" && path === "/game.html") {
          res.setHeader("content-type", "text/html; charset=utf-8");
          res.end(page());
          return;
        }
        if (req.method === "POST" && path === "/__docket/release-refund") {
          const today = new Date().toISOString().slice(0, 10);
          execFile(resolve(ROOT, ".venv/bin/python"), ["-m", "seed.release_refund", today], { cwd: ROOT },
            (err, stdout, stderr) => {
              res.statusCode = err ? 500 : 200;
              res.end(err ? (stderr || err.message).slice(-400) : stdout);
            });
          return;
        }
        next();
      });
    },
    generateBundle() {
      this.emitFile({ type: "asset", fileName: "game.html", source: page() });
    },
  };
}

// Reads CONVEX_URL from the repo-root .env, the same one the agents use.
// Pages: the dashboard (index.html), the public waitlist (waitlist.html) and the Hearing game (game.html).
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ROOT, "CONVEX_URL");
  return {
    plugins: [react(), hearingGame(env.CONVEX_URL)],
    envDir: "..",
    envPrefix: "CONVEX_URL",
    build: {
      rollupOptions: {
        input: {
          main: resolve(__dirname, "index.html"),
          waitlist: resolve(__dirname, "waitlist.html"),
        },
      },
    },
  };
});
