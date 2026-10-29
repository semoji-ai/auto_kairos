// node tools/reach.js story.html
// Plays the story at 10 fps and lists every {hand:[X,Y,Z]} target that the arm cannot reach once it has arrived
// (the hand then stops short in mid-air). Nothing listed = every hand target is reachable.
const { open } = require('./pw');
(async () => {
  const { browser, page } = await open(process.argv[2]);
  const rows = await page.evaluate(() => { const acc = {};
    for (let t = 0; t < DUR; t += 0.1) { window.MISS = []; renderAt(t); const s = SCN.filter(s => t >= s.t0).pop();
      for (const [who, arm, miss, sh, rc] of window.MISS) { const k = s.tag + ' ' + s.title + ' | ' + who + ' ' + arm, a = acc[k] || (acc[k] = { t0: t, t1: t, max: 0, loc: +(t - s.t0).toFixed(1) }); a.t1 = t; if (miss >= a.max) { a.max = miss; a.sh = sh; a.rc = rc; } } }
    return Object.entries(acc).map(([k, a]) => `${k} | short by up to ${a.max.toFixed(2)} | ${a.t0.toFixed(1)}–${a.t1.toFixed(1)}s (scene time from ${a.loc}s) | shoulder [X,Y,Z]=[${a.sh}], reach ${a.rc}`); });
  console.log(rows.length ? rows.join('\n') + '\n→ move the character or the object, bend (lean / lower hipY), or give the target a Z nearer the shoulder. See README "손이 닿는 범위".' : 'OK: every hand target is within reach');
  await browser.close();
})();
