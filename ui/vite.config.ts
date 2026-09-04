import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The production bundle is served by the FastAPI backend at "/" (StaticFiles, html=True).
// Relative base + HashRouter means deep links work from a static mount.
export default defineConfig({
  plugins: [react()],
  base: "./",
  build: { outDir: "dist", emptyOutDir: true },
  server: {
    port: 5173,
    proxy: { "/api": { target: "http://127.0.0.1:8765", changeOrigin: false } },
  },
});
