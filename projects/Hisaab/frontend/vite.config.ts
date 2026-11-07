import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server proxies /api and /results to the FastAPI backend (uvicorn app.main:app --port 8000)
export default defineConfig({
  plugins: [react()],
  css: { postcss: {} },   // isolate from any parent-directory postcss config
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
      "/results": "http://localhost:8000",
    },
  },
});
