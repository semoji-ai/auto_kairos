/**
 * 개별 씬 비디오 클립 렌더러
 *
 * 사용법:
 *   node render_scene.js <sceneNumber> <outputPath>
 *   node render_scene.js 4 ../output/캠핑산업의_몰락/visualizations/scene_004.mp4
 *   node render_scene.js all ../output/캠핑산업의_몰락/visualizations/
 *
 * manifest.json은 public/manifest.json에서 자동 로드
 */
const { bundle } = require("@remotion/bundler");
const { renderMedia, selectComposition } = require("@remotion/renderer");
const path = require("path");
const fs = require("fs");

async function main() {
  const args = process.argv.slice(2);
  if (args.length < 2) {
    console.error("Usage: node render_scene.js <sceneNumber|all|viz> <outputPath>");
    process.exit(1);
  }

  const sceneArg = args[0];
  const outputArg = args[1];

  // Load manifest
  const manifestPath = path.resolve(__dirname, "public/manifest.json");
  if (!fs.existsSync(manifestPath)) {
    console.error("manifest.json not found at: " + manifestPath);
    process.exit(1);
  }
  const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
  const fps = manifest.meta?.fps || 30;

  // Determine which scenes to render
  let sceneNumbers = [];
  if (sceneArg === "all") {
    sceneNumbers = manifest.scenes.map((s) => s.sceneNumber);
  } else if (sceneArg === "viz") {
    // Only visualization scenes
    sceneNumbers = manifest.scenes
      .filter((s) => s.visualization)
      .map((s) => s.sceneNumber);
  } else {
    sceneNumbers = sceneArg.split(",").map(Number);
  }

  if (sceneNumbers.length === 0) {
    console.log("No scenes to render.");
    return;
  }

  console.log(`Rendering ${sceneNumbers.length} scene(s): [${sceneNumbers.join(", ")}]`);

  // Bundle once
  console.log("Bundling...");
  const bundled = await bundle({
    entryPoint: path.resolve(__dirname, "src/index.ts"),
    webpackOverride: (config) => config,
  });
  console.log("Bundle done.");

  const subtitleConfig = manifest.subtitleConfig || {
    visible: true,
    fontFamily: "'Noto Sans KR', 'Apple SD Gothic Neo', sans-serif",
    fontSize: 44, fontWeight: 700, color: "white",
    strokeColor: "#3D3B2F", strokeWidth: 0,
    keywordColor: "#F7D94C", keywordStrokeColor: "#5A4B00",
    bottomOffset: 80, maxWidth: "85%", lineHeight: 1.5,
  };

  const results = [];

  for (const sceneNum of sceneNumbers) {
    const scene = manifest.scenes.find((s) => s.sceneNumber === sceneNum);
    if (!scene) {
      console.log(`  Scene ${sceneNum}: not found, skipping.`);
      continue;
    }

    const compositionId = `Scene-${sceneNum}`;
    const inputProps = { manifest, sceneNumber: sceneNum, subtitleConfig };

    // Determine output path
    let outputPath;
    if (sceneNumbers.length === 1 && !outputArg.endsWith("/")) {
      outputPath = path.resolve(outputArg);
    } else {
      const dir = path.resolve(outputArg);
      fs.mkdirSync(dir, { recursive: true });
      outputPath = path.join(dir, `scene_${String(sceneNum).padStart(3, "0")}.mp4`);
    }

    try {
      const composition = await selectComposition({
        serveUrl: bundled,
        id: compositionId,
        inputProps,
      });

      const durationSec = (composition.durationInFrames / fps).toFixed(1);
      const layout = scene.visualization?.creative?.layout || "image";
      console.log(`  Scene ${sceneNum} [${layout}]: ${composition.durationInFrames}f (${durationSec}s) → ${path.basename(outputPath)}`);

      await renderMedia({
        composition,
        serveUrl: bundled,
        codec: "h264",
        outputLocation: outputPath,
        inputProps,
        concurrency: 2,
      });

      results.push({ sceneNumber: sceneNum, status: "ok", path: outputPath });
      console.log(`    ✓ Done`);
    } catch (err) {
      results.push({ sceneNumber: sceneNum, status: "error", error: err.message });
      console.error(`    ✗ Error: ${err.message}`);
    }
  }

  console.log(`\nComplete: ${results.filter((r) => r.status === "ok").length}/${sceneNumbers.length} rendered`);

  // Write results JSON
  const resultsPath = path.resolve(outputArg.endsWith("/") ? outputArg : path.dirname(outputArg), "render_results.json");
  fs.writeFileSync(resultsPath, JSON.stringify(results, null, 2));
}

main().catch((err) => {
  console.error(err.message);
  process.exit(1);
});
