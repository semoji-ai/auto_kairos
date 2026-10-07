// node tools/strip.js story.html t0 t1 [n=8] out.png   -> n evenly spaced frames between t0 and t1 on one sheet
// Use it to check a MOVE (walk-in, reach, hand-off, turn): stills at key moments do not show a bad in-between.
const { open } = require('./pw');
const { execFileSync } = require('child_process');
const fs = require('fs'), os = require('os'), path = require('path');
(async () => {
  const a = process.argv.slice(2), file = a[0], t0 = +a[1], t1 = +a[2], n = a.length > 4 ? +a[3] : 8, out = a[a.length - 1];
  const { browser, page } = await open(file, '?nosub=1');
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'strip-')), files = [];
  for (let i = 0; i < n; i++) { const t = t0 + (t1 - t0) * i / Math.max(1, n - 1), f = path.join(dir, i + '.png'); await page.evaluate(t => renderAt(t), t); await page.screenshot({ path: f }); files.push(f); }
  await browser.close();
  const cols = Math.min(4, n), args = ['-y', '-loglevel', 'error'];
  for (const f of files) args.push('-i', f);
  args.push('-filter_complex', files.map((_, i) => `[${i}]`).join('') + `xstack=inputs=${n}:layout=${files.map((_, i) => `${(i % cols) * 1920}_${Math.floor(i / cols) * 1080}`).join('|')}:fill=0xF3EFE6,scale=${cols * 960}:-1`, out);
  if (n === 1) fs.copyFileSync(files[0], out); else execFileSync('ffmpeg', args);
  console.log(out, n, 'frames', t0, '→', t1);
})();
