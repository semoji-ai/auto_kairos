// 사용: node stills.mjs 100 250 400 ...  → video/out/explainer_demo_stills/f####.jpg
import { bundle } from "@remotion/bundler";
import { renderStill, selectComposition } from "@remotion/renderer";
import path from "path";
import { fileURLToPath } from "url";
const V = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../video");
const frames = process.argv.slice(2).map(Number);
const serveUrl = await bundle({ entryPoint: path.join(V, "src/index.ts"), publicDir: path.join(V, "public") });
const comp = await selectComposition({ serveUrl, id: "ExplainerDemo", chromiumOptions: { gl: "angle" } });
for (const frame of frames) {
  const out = path.join(V, `out/explainer_demo_stills/f${String(frame).padStart(4, "0")}.jpg`);
  await renderStill({ composition: comp, serveUrl, output: out, frame, imageFormat: "jpeg", jpegQuality: 85, chromiumOptions: { gl: "angle" }, timeoutInMilliseconds: 120000 });
  console.log("ok", out);
}
