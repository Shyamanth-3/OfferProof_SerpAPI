import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // tesseract.js is only imported when a screenshot is added. Without this, the dev server discovers it at that moment,
  // re-bundles, and reloads the page mid-read, so the first screenshot appears to do nothing.
  optimizeDeps: { include: ["tesseract.js"] },
  server: { port: 5173, proxy: { "/api": "http://localhost:8000" } },
});
