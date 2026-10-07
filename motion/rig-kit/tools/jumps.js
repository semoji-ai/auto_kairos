// node tools/jumps.js story.html out.mp4 [threshold=0.012]
// Finds frames where the picture changes abruptly, and drops the ones that are expected:
// the fade at each scene boundary (first 0.3 s / last 0.25 s of a scene). What is left is worth looking at:
// a pose jump (overlapping keys), a prop swap, or a big card popping in (fine if intended).
const { open } = require('./pw');
const { spawnSync } = require('child_process');
(async () => {
  const [file, mp4, th] = process.argv.slice(2);
  const { browser, page } = await open(file);
  const sc = await page.evaluate(() => SCN.map(s => [s.t0, s.t0 + s.dur, s.tag + ' ' + s.title]));
  await browser.close();
  const r = spawnSync('ffmpeg', ['-hide_banner', '-i', mp4, '-vf', `select='gt(scene,${th || 0.012})',metadata=print:file=-`, '-f', 'null', '-'], { encoding: 'utf8', maxBuffer: 1 << 26 });
  const hits = []; let cur = null;
  for (const l of r.stdout.split('\n')) { const m = l.match(/pts_time:([0-9.]+)/); if (m) cur = +m[1]; const s = l.match(/scene_score=([0-9.]+)/); if (s && cur !== null) hits.push([cur, +s[1]]); }
  const inFade = t => sc.some(([a, b]) => (t >= a - 0.02 && t < a + 0.3) || (t > b - 0.25 && t <= b + 0.02));
  const left = hits.filter(h => !inFade(h[0]));
  console.log(`${hits.length} abrupt frames, ${hits.length - left.length} at scene fades (expected)`);
  for (const [t, s] of left) { const k = sc.find(([a, b]) => t >= a && t < b) || sc[sc.length - 1]; console.log(`  ${t.toFixed(3)}s  score ${s.toFixed(3)}  in ${k[2]} (scene time ${(t - k[0]).toFixed(2)}s)  → compare frames at ${(t - 1 / 60).toFixed(3)} and ${t.toFixed(3)}`); }
  if (!left.length) console.log('OK: nothing abrupt inside the scenes');
})();
