// node tools/render.js story.html out.mp4 [fps=60] [query]   -> deterministic frame-by-frame render (H.264, 1920x1080)
const { open } = require('./pw');
const { spawn } = require('child_process');
(async () => {
  const [file, out, fpsArg, query] = process.argv.slice(2), fps = +(fpsArg || 60);
  const { browser, page, errs } = await open(file, query);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'png', '-i', '-',
    '-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-movflags', '+faststart', out], { stdio: ['pipe', 'inherit', 'inherit'] });
  let n = 0, done = false;
  while (!done && n < fps * 600) {
    const r = await page.evaluate(dt => { const f = step(dt); return [f, document.getElementById('cv').toDataURL('image/png')]; }, 1 / fps);
    done = r[0];
    const buf = Buffer.from(r[1].split(',')[1], 'base64');
    if (!ff.stdin.write(buf)) await new Promise(res => ff.stdin.once('drain', res));
    n++;
  }
  ff.stdin.end(); await new Promise(res => ff.on('close', res)); await browser.close();
  console.log(out, n, 'frames', errs.length ? 'WITH PAGE ERRORS' : '');
})();
