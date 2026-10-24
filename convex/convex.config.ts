import { defineApp } from "convex/server";
import { v } from "convex/values";

// CARTESIA_TOOL_TOKEN: shared secret the Cartesia voice agent sends as "Authorization: Bearer <token>"
// when it calls our webhook tools (convex/http.ts). Set it with `npx convex env set CARTESIA_TOOL_TOKEN <value>`.
const app = defineApp({
  env: {
    CARTESIA_TOOL_TOKEN: v.optional(v.string()),
  },
});

export default app;
