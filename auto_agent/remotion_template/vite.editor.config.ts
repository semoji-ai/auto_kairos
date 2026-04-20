import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  publicDir: false,
  build: {
    lib: {
      entry: path.resolve(__dirname, "src/editor/EditorApp.tsx"),
      name: "SceneEditor",
      fileName: () => "scene-editor.js",
      formats: ["iife"],
    },
    outDir: path.resolve(__dirname, "../auto_agent/dashboard/static"),
    emptyOutDir: false,
    rollupOptions: {
      output: {
        // IIFE 형태로 단일 파일 출력
        inlineDynamicImports: true,
        // CSS를 JS에 인라인
        assetFileNames: "scene-editor.[ext]",
      },
    },
    // maplibre-gl 등 무거운 패키지 트리쉐이킹
    commonjsOptions: {
      include: [/node_modules/],
    },
  },
  resolve: {
    alias: {
      // Remotion src 디렉토리 직접 참조
      "@": path.resolve(__dirname, "src"),
    },
  },
  define: {
    "process.env.NODE_ENV": JSON.stringify("production"),
  },
});
