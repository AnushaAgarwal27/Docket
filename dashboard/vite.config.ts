import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Reads CONVEX_URL from the repo-root .env, the same one the agents use.
export default defineConfig({
  plugins: [react()],
  envDir: "..",
  envPrefix: "CONVEX_URL",
});
