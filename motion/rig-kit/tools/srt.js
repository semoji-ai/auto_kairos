// node tools/srt.js story.html out.srt   -> narration lines with the time slots the animation was built on
const { open } = require('./pw');
const fs = require('fs');
(async () => {
  const [file, out] = process.argv.slice(2);
  const { browser, page } = await open(file);
  const N = await page.evaluate(() => NARR.map(n => [n.t0, n.t1, n.text]));
  const tc = x => { const h = Math.floor(x / 3600), m = Math.floor(x % 3600 / 60), s = x % 60; return String(h).padStart(2, '0') + ':' + String(m).padStart(2, '0') + ':' + s.toFixed(3).padStart(6, '0').replace('.', ','); };
  fs.writeFileSync(out, N.map((n, i) => `${i + 1}\n${tc(n[0])} --> ${tc(n[1])}\n${n[2]}\n`).join('\n'));
  await browser.close(); console.log(out, N.length, 'lines');
})();
