// node tools/board.js story.html board.png [cols=4]   -> one key frame per narration line (or per scene.board time), tiled (for a quick look at the whole piece)
const { open } = require('./pw');
const { execFileSync } = require('child_process');
const fs = require('fs'), os = require('os'), path = require('path');
(async () => {
  const [file, out, colsArg] = process.argv.slice(2), cols = +(colsArg || 4);
  const { browser, page } = await open(file);
  // a scene may name its own key moments: board:[1.2,3.4] (scene time). Otherwise: 80% into each narration line.
  const T = await page.evaluate(() => SCN.flatMap(s => s.board ? s.board.map(t => s.t0 + t) : s.N.map(n => s.t0 + n.t0 + (n.t1 - n.t0) * 0.8)));
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'board-')), files = [];
  for (let i = 0; i < T.length; i++) { const t = T[i], f = path.join(dir, i + '.png'); await page.evaluate(t => renderAt(t), t); await page.screenshot({ path: f }); files.push(f); }
  await browser.close();
  const lay = files.map((_, i) => `${(i % cols) * 1920}_${Math.floor(i / cols) * 1080}`).join('|'), args = ['-y', '-loglevel', 'error'];
  for (const f of files) args.push('-i', f);
  args.push('-filter_complex', files.map((_, i) => `[${i}]`).join('') + `xstack=inputs=${files.length}:layout=${lay}:fill=0xF3EFE6,scale=${Math.min(3840, cols * 960)}:-1`, out);
  if (files.length === 1) fs.copyFileSync(files[0], out); else execFileSync('ffmpeg', args);
  console.log(out, files.length, 'frames');
})();
