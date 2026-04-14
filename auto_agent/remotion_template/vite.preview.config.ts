import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  root: path.resolve(__dirname, "src/preview"),
  base: "/static/preview/",
  build: {
    outDir: path.resolve(__dirname, "../auto_agent/dashboard/static/preview"),
    emptyDirBeforeWrite: true,
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
});
