// Builds the Hearing game as its own site (docket-game.vercel.app): the game at /, opening on the
// live case, reading the Convex student file and posting the refund through /api/release-refund.
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";

const convex = process.env.CONVEX_URL;
if (!convex) throw new Error("CONVEX_URL is not set");
const meta = [
  `<meta name="convex-url" content="${convex}">`,
  `<meta name="docket-default-case" content="live">`,
  `<meta name="docket-refund-endpoint" content="/api/release-refund">`,
].join("\n");
const html = readFileSync("docket-game.html", "utf8").replace("<head>", `<head>\n${meta}`);
mkdirSync("game-site", { recursive: true });
writeFileSync("game-site/index.html", html);
console.log("game-site/index.html written");
