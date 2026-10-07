// finds playwright + a chromium that actually launches (cloud workspaces ship one at /opt/pw-browsers)
const { execSync } = require('child_process');
function lib() {
  const tries = ['playwright', process.env.PLAYWRIGHT_PATH, '/home/claude/.npm-global/lib/node_modules/playwright'];
  try { tries.push(execSync('npm root -g').toString().trim() + '/playwright'); } catch (e) {}
  for (const p of tries.filter(Boolean)) { try { return require(p); } catch (e) {} }
  throw new Error('playwright not found. Run: PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm i -g playwright');
}
// chromium executables already downloaded by any playwright version (version mismatch is fine for file:// pages)
function cachedChromiums() {
  const fs = require('fs'), path = require('path'), os = require('os');
  const roots = [process.env.PLAYWRIGHT_BROWSERS_PATH, path.join(os.homedir(), 'Library/Caches/ms-playwright'), path.join(os.homedir(), '.cache/ms-playwright')].filter(Boolean);
  const rel = ['chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing',
    'chrome-mac-x64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing',
    'chrome-mac/Chromium.app/Contents/MacOS/Chromium', 'chrome-linux/chrome', 'chrome-linux64/chrome'];
  const out = [];
  for (const r of roots) {
    let dirs = [];
    try { dirs = fs.readdirSync(r).filter(d => /^chromium-\d+$/.test(d)).sort().reverse(); } catch (e) { continue; }
    for (const d of dirs) for (const p of rel) { const f = path.join(r, d, p); if (fs.existsSync(f)) out.push(f); }
  }
  return out;
}
async function open(file, query, w, h) {
  const { chromium } = lib();
  let browser;
  let lastErr;
  // 1) playwright's own browser  2) $CHROMIUM  3) cloud path  4) any cached chromium (macOS/Linux ms-playwright cache)
  const paths = [undefined, process.env.CHROMIUM, '/opt/pw-browsers/chromium', ...cachedChromiums()];
  for (const executablePath of paths) {
    try { browser = await chromium.launch({ executablePath, args: ['--disable-gpu-vsync'] }); break; }
    catch (e) { lastErr = e; }
  }
  if (!browser) throw lastErr;
  const page = await browser.newPage({ viewport: { width: w || 1920, height: h || 1080 } });
  const errs = [];
  page.on('pageerror', e => { errs.push(e.message); console.log('PAGE ERROR:', e.message); });
  await page.goto('file://' + require('path').resolve(file) + (query || ''));
  return { browser, page, errs };
}
module.exports = { open };
