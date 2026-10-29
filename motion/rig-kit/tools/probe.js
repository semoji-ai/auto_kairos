// node tools/probe.js engine.html ['["직장인","화가"]'] [walk=0]
// Turns each character through 360° in 0.5° steps and reports yaw angles where far more pixels change than usual
// (= something flips layers or pops). Run after touching the rig or adding a character. Empty list after the name = clean.
const { open } = require('./pw');
(async () => {
  const [file, namesArg, walkArg] = process.argv.slice(2);
  const { browser, page } = await open(file);
  const res = await page.evaluate(([names, walk]) => {
    const out = [], list = names || CAST.map(k => k.name);
    const draw = (ch, deg) => { c.setTransform(1, 0, 0, 1, 0, 0); c.fillStyle = '#fff'; c.fillRect(0, 0, 700, 900); actor(ch, { yaw: deg * Math.PI / 180, walk, seed: 0 }, 0.3, 350, 800, 170); return c.getImageData(0, 0, 700, 900).data; };
    for (const n of list) { const ch = CAST.find(k => k.name === n); let prev = draw(ch, 0); const J = [];
      for (let d = 0.5; d <= 360; d += 0.5) { const cur = draw(ch, d); let cnt = 0; for (let i = 0; i < cur.length; i += 4) if (Math.abs(cur[i] - prev[i]) + Math.abs(cur[i + 1] - prev[i + 1]) + Math.abs(cur[i + 2] - prev[i + 2]) > 90) cnt++; J.push([d, cnt]); prev = cur; }
      const s = J.map(j => j[1]).sort((a, b) => a - b), med = s[s.length >> 1];
      out.push(n + ' median=' + med + ' | ' + J.filter(j => j[1] > med * 3 + 150).map(j => j[0] + '°:' + j[1] + 'px').join('  ')); }
    return out;
  }, [namesArg ? JSON.parse(namesArg) : null, +(walkArg || 0)]);
  console.log(res.join('\n')); await browser.close();
})();
