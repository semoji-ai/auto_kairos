// node tools/shot.js story.html info                          -> scene starts, durations and narration time slots (JSON)
// node tools/shot.js story.html '[[1.6,"a.png"],[4.2,"b.png"]]' -> still frames at absolute times (seconds)
// optional 3rd arg: query string, e.g. '?nosub=1'
const { open } = require('./pw');
(async () => {
  const [file, jobs, query] = process.argv.slice(2);
  const { browser, page } = await open(file, query);
  if (jobs === 'info') console.log(JSON.stringify(await page.evaluate(() => ({ DUR: +DUR.toFixed(2), scenes: SCN.map(s => ({ tag: s.tag, title: s.title, t0: +s.t0.toFixed(2), dur: +s.dur.toFixed(2) })), NARR: NARR.map(n => ({ t0: +n.t0.toFixed(2), t1: +n.t1.toFixed(2), text: n.text })) })), null, 1));
  else for (const [t, out] of JSON.parse(jobs)) { await page.evaluate(t => renderAt(t), t); await page.screenshot({ path: out }); }
  await browser.close();
})();
