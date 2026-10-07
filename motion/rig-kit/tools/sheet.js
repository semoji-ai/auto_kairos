// node tools/sheet.js page.html cast.png props.png
// Draws every character in CAST (including ones a story file pushed) and every prop, with names. Look before you cast.
const { open } = require('./pw');
(async () => {
  const [file, castOut, propsOut] = process.argv.slice(2);
  const { browser, page } = await open(file);
  await page.evaluate(() => { c.setTransform(1, 0, 0, 1, 0, 0); c.fillStyle = BG; c.fillRect(0, 0, W, H);
    const n = CAST.length, cols = Math.ceil(n / 2), cw = W / cols;
    CAST.forEach((ch, i) => { const col = i % cols, row = (i / cols) | 0, x = cw * (col + 0.5), gy = row ? 1010 : 480, U = Math.min(112, cw / 2.6);
      actor(ch, { yaw: (row ? -25 : 25) * Math.PI / 180, walk: 0, seed: 0 }, 0.5, x, gy, U); c.font = `900 26px ${FONT}`; c.fillStyle = INK; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText(ch.name, x, gy + 42); }); });
  await page.screenshot({ path: castOut });
  if (propsOut) { await page.evaluate(() => { c.setTransform(1, 0, 0, 1, 0, 0); c.fillStyle = BG; c.fillRect(0, 0, W, H);
    const P = { propRot: 0, fill: 0.75, steam: 0, t: 0, sy: 1, sway: 0 }, base = { cup: () => { c.translate(0, -0.1); cupShape(0, 0) }, case: () => { c.translate(0, 0.3); caseShape(0.8) }, parcel: () => parcelShape(), bag: () => { c.translate(0, 0.26); bagShape() } };
    const names = Object.keys(base).concat(Object.keys(PROPS)), cols = Math.ceil(names.length / 2), cw = W / cols;
    names.forEach((nm, i) => { const x = cw * ((i % cols) + 0.5), y = (i / cols | 0) ? 760 : 300, U = 130; c.save(); c.translate(x, y); c.scale(U, U);
      c.beginPath(); c.arc(0, 0, 0.03, 0, TAU); c.fillStyle = '#FF2D2D'; c.fill(); if (base[nm]) base[nm](); else PROPS[nm](P, 1, 0); c.restore();
      c.font = `900 28px ${FONT}`; c.fillStyle = INK; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText("'" + nm + "'", x, y + 150); });
    c.font = `700 24px ${FONT}`; c.fillStyle = 'rgba(59,36,22,0.6)'; c.fillText('빨간 점 = 손이 쥐는 지점(손이 그 위에 그려진다)', W / 2, 1030); });
    await page.screenshot({ path: propsOut }); }
  await browser.close(); console.log(castOut, propsOut || '');
})();
