#!/usr/bin/env node
// Drive a game page headlessly through the window.G hooks, screenshot it, and fail on
// any page error. Headless tabs run no requestAnimationFrame, so every frame here is
// pushed by G.step(): read state numbers first, treat screenshots as supporting evidence.
//
// Usage:
//   node scripts/play-check.mjs <url> --shot out.png [--script steps.js] [--size 1280x800] [--demo [frames]]
// steps.js is evaluated in the page after G.ready, as the body of an async function
// with G in scope, e.g.  G.start(); G.step(30); G.advance(); G.hold('KeyW'); G.step(120);
// Its return value is printed as JSON. A file:// URL works too (single-HTML builds).
// --demo runs the game's own autoplay (G.demo) to its end before the script, logic-only,
// and fails if it has not finished within the frame budget (default 36000 = 10 game minutes).
import fs from 'node:fs';
import { chromium } from 'playwright';

const args = process.argv.slice(2);
const url = args[0];
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
if (!url || url.startsWith('--')) { console.error('usage: play-check.mjs <url> --shot out.png [--script steps.js] [--size WxH]'); process.exit(2); }
const [w, h] = opt('--size', '1280x800').split('x').map(Number);
const shot = opt('--shot');
const script = opt('--script') ? fs.readFileSync(opt('--script'), 'utf8') : '';
const demoAt = args.indexOf('--demo');
const demoBudget = demoAt < 0 ? 0 : Number(/^\d+$/.test(args[demoAt + 1] || '') ? args[demoAt + 1] : 36000);

// --disable-gpu: macOS denies Playwright's libEGL and a dying GPU process kills the page;
// SwiftShader gives WebGL a deterministic software path instead.
const browser = await chromium.launch({ args: ['--disable-gpu', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--autoplay-policy=no-user-gesture-required'] });
const page = await browser.newPage({ viewport: { width: w, height: h } });
const problems = [];
page.on('pageerror', (e) => problems.push(`pageerror: ${e.message}`));
page.on('console', (m) => { if (m.type() === 'error') problems.push(`console: ${m.text()}`); });
const warnings = [];
// three.js's FileLoader re-wraps the response stream for progress events; Chromium then
// sometimes reports the finished request as ERR_ABORTED although the asset loaded. A real
// load failure rejects the loader and lands in G.errors, so treat ERR_ABORTED as a warning.
page.on('requestfailed', (r) => { const t = r.failure()?.errorText || ''; (t.includes('ERR_ABORTED') ? warnings : problems).push(`requestfailed: ${r.url()} ${t}`); });
const external = [];
page.on('request', (r) => {
  const u = r.url();
  if (url.startsWith('file:') && u.startsWith('file:') && u.split('?')[0] !== url.split('?')[0]) external.push(`${u} (a single-file build must not read sibling files)`);
  else if (!/^(data:|blob:|file:|https?:\/\/(localhost|127\.0\.0\.1))/.test(u)) external.push(u);
});

try {
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForFunction(() => window.G && (window.G.ready || window.G.errors.length), null, { timeout: 60000 });
  const result = await page.evaluate(async ({ body, demoBudget }) => {
    const G = window.G; G.step?.(2);
    let demo = null;
    if (demoBudget) {
      if (!G.demo) throw new Error('--demo: this page has no G.demo autoplay (see the starter src/autoplay.js)');
      G.demo.start(); let frames = 0;
      while (G.demo.running && frames < demoBudget) { G.upd(60); frames += 60; }
      demo = { frames, finished: !G.demo.running };
      G.step(1);
    }
    const r = await new Function('G', `return (async () => { ${body} })()`)(G);
    return { result: r ?? null, demo, state: G.state?.() ?? null, errors: G.errors };
  }, { body: script, demoBudget });
  if (shot) await page.screenshot({ path: shot, timeout: 20000 }).catch(async () => {
    // screenshot() waits on fonts internally; fall back to raw CDP capture
    const cdp = await page.context().newCDPSession(page);
    const { data } = await cdp.send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(shot, Buffer.from(data, 'base64'));
  });
  console.log(JSON.stringify(result, null, 2));
  if (external.length) problems.push(`external requests (a shipped game must make none): ${[...new Set(external)].join(', ')}`);
  if (result.demo && !result.demo.finished) problems.push(`demo still running after ${result.demo.frames} frames: its plan() never reaches an end`);
  if (result.errors?.length) problems.push(...result.errors.map((e) => `G.errors: ${e}`));
} catch (e) {
  problems.push(`check failed: ${e.message}`);
} finally {
  await browser.close();
}
if (warnings.length) console.warn(`warnings (non-fatal):\n  ${warnings.join('\n  ')}`);
if (problems.length) { console.error(problems.join('\n')); process.exit(1); }
console.log(`ok${shot ? ` -> ${shot}` : ''}`);
