import { resolve } from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Reads CONVEX_URL from the repo-root .env, the same one the agents use.
// Two pages: the dashboard (index.html) and the public waitlist (waitlist.html).
export default defineConfig({
  plugins: [react()],
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
});
