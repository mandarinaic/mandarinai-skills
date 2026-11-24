#!/usr/bin/env node
// Drive a game page headlessly through the window.G hooks, screenshot it, and fail on
// any page error. Headless tabs run no requestAnimationFrame, so every frame here is
// pushed by G.step(): read state numbers first, treat screenshots as supporting evidence.
//
// Usage:
//   node scripts/play-check.mjs <url> --shot out.png [--script steps.js] [--size 1280x800] [--demo [frames]]
//   node scripts/play-check.mjs <url> --poster <frames> --shot poster.png [--size 1200x630]
//   node scripts/play-check.mjs <url> --bot [accuracy] [--runs 3] [--seed 1] [--time lo-hi] [--budget frames]
//   any of the above with --device phone,laptop (instead of --size) to repeat the check per device
//   --demo or --bot with --motion to lint every actor's motion on every step of the run
// steps.js is evaluated in the page after G.ready, as the body of an async function
// with G in scope, e.g.  G.start(); G.step(30); G.advance(); G.hold('KeyW'); G.step(120);
// Its return value is printed as JSON. A file:// URL works too (single-HTML builds).
// --demo runs the game's own autoplay (G.demo) to its end before the script, logic-only,
// and fails if it has not finished within the frame budget (default 36000 = 10 game minutes).
// --poster plays exactly <frames> demo steps, then shoots: the same frames give the same
// image, recorded next to it as <shot>.json (method, frames, size, sha256, state).
// --bot plays the demo route as a learner (?bot=<accuracy>&seed=<n>, default 0.7): reaction
// pauses, imprecise walking, slower reading, wrong turns at 1 - accuracy. Each run gets its own
// seed (seed, seed+1, ...) in a fresh page; the report lists game seconds per run. It fails when
// a run never finishes (the game trapped the learner) or, with --time, lands outside lo-hi seconds.
// --motion samples G.motion() (one entry per actor, motion.js sample()) after every logic step of
// the --demo or --bot run and fails on what a viewer would see as a glitch: snaps (teleports
// that are not place()), instant about-faces, feet under the ground, squash past its limits,
// NaN. See scripts/motion-lint.mjs for the thresholds.
// --device runs the whole check once per preset: phone (390x844, dpr 2, touch), phone-landscape,
// tablet (820x1180, touch), laptop (1280x800). With several devices, shots get a -<device> suffix.
// On every device the final screen must fit: visible text, buttons or images reaching outside the
// viewport, text drawn over other text, or a page that scrolls sideways, fail the check. Use a --script to stop on other screens.
// The page opens with ?paused so its real-time loop never runs: every frame is pushed here,
// and the screenshot shows exactly the state that is printed.
import fs from 'node:fs';
import crypto from 'node:crypto';
import { chromium } from 'playwright';
import { lintMotion } from './motion-lint.mjs';

const args = process.argv.slice(2);
const url = args[0];
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const flagNum = (k, d) => { const i = args.indexOf(k); if (i < 0) return 0; const v = args[i + 1]; return /^[\d.]+$/.test(v || '') ? Number(v) : d; };
const fail = (msg) => { console.error(msg); process.exit(2); };
if (!url || url.startsWith('--')) fail('usage: play-check.mjs <url> --shot out.png [--script steps.js] [--size WxH] [--demo [frames]] [--poster frames] [--bot [accuracy]]');
const DEVICES = {
  laptop: { viewport: { width: 1280, height: 800 } },
  phone: { viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true },
  'phone-landscape': { viewport: { width: 844, height: 390 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true },
  tablet: { viewport: { width: 820, height: 1180 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true },
};
if (opt('--device') && opt('--size')) fail('use --device or --size, not both');
const deviceNames = (opt('--device') || '').split(',').filter(Boolean);
for (const d of deviceNames) if (!DEVICES[d]) fail(`unknown --device ${d}; one of ${Object.keys(DEVICES).join(', ')}`);
const [sw, sh] = opt('--size', '1280x800').split('x').map(Number);
const devices = deviceNames.length ? deviceNames.map((name) => ({ name, ...DEVICES[name] })) : [{ name: `${sw}x${sh}`, viewport: { width: sw, height: sh } }];
let device = devices[0];   // the device the current pass runs on
const shotArg = opt('--shot');
// one shot per device: out.png -> out-phone.png, out-laptop.png
const shotFor = (d) => (shotArg && devices.length > 1 ? shotArg.replace(/(\.\w+)?$/, `-${d.name}$1`) : shotArg);
const script = opt('--script') ? fs.readFileSync(opt('--script'), 'utf8') : '';
const demoBudget = flagNum('--demo', 36000);
const posterAt = Number(opt('--poster', 0));
const botAcc = flagNum('--bot', 0.7);
const runs = Number(opt('--runs', 3)), seed0 = Number(opt('--seed', 1)), budget = Number(opt('--budget', 36000));
const timeWindow = opt('--time') ? opt('--time').split('-').map(Number) : null;
if (opt('--poster') !== undefined && !(posterAt > 0)) fail('--poster needs a frame count > 0');
if (posterAt && !shotArg) fail('--poster needs --shot <file>');
if ([posterAt, demoBudget, botAcc].filter(Boolean).length > 1) fail('use one of --demo, --poster, --bot');
const motion = args.includes('--motion');
if (motion && !demoBudget && !botAcc) fail('--motion needs --demo or --bot: it lints the frames of that run');
if (botAcc && !(botAcc > 0 && botAcc <= 1)) fail('--bot accuracy must be in (0, 1]');
if (timeWindow && !(timeWindow.length === 2 && timeWindow[0] < timeWindow[1])) fail('--time needs lo-hi seconds, e.g. --time 60-600');

// --disable-gpu: macOS denies Playwright's libEGL and a dying GPU process kills the page;
// SwiftShader gives WebGL a deterministic software path instead.
const browser = await chromium.launch({ args: ['--disable-gpu', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--autoplay-policy=no-user-gesture-required'] });
const problems = [], warnings = [], external = [];

// A fresh page on the game, real-time loop off, G ready. Collects errors and stray requests.
async function openGame(query = {}) {
  const { name, ...context } = device;
  const page = await browser.newPage(context);
  page.on('pageerror', (e) => problems.push(`pageerror: ${e.message}`));
  page.on('console', (m) => { if (m.type() === 'error') problems.push(`console: ${m.text()}`); });
  // three.js's FileLoader re-wraps the response stream for progress events; Chromium then
  // sometimes reports the finished request as ERR_ABORTED although the asset loaded. A real
  // load failure rejects the loader and lands in G.errors, so treat ERR_ABORTED as a warning.
  page.on('requestfailed', (r) => { const t = r.failure()?.errorText || ''; (t.includes('ERR_ABORTED') ? warnings : problems).push(`requestfailed: ${r.url()} ${t}`); });
  page.on('request', (r) => {
    const u = r.url();
    if (url.startsWith('file:') && u.startsWith('file:') && u.split('?')[0] !== url.split('?')[0]) external.push(`${u} (a single-file build must not read sibling files)`);
    else if (!/^(data:|blob:|file:|https?:\/\/(localhost|127\.0\.0\.1))/.test(u)) external.push(u);
  });
  const open = new URL(url); open.searchParams.set('paused', '');
  for (const [k, v] of Object.entries(query)) open.searchParams.set(k, v);
  await page.goto(open.href, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForFunction(() => window.G && (window.G.ready || window.G.errors.length), null, { timeout: 60000 });
  return page;
}

async function screenshot(page, file) {
  await page.screenshot({ path: file, timeout: 20000 }).catch(async () => {
    // screenshot() waits on fonts internally; fall back to raw CDP capture
    const cdp = await page.context().newCDPSession(page);
    const { data } = await cdp.send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(file, Buffer.from(data, 'base64'));
  });
}

// The final screen must fit the device: no visible text, control or image outside the viewport
// (scrolling panels excepted), no text drawn over other text, and no sideways page scroll.
const LAYOUT = () => {
  const W = innerWidth, H = innerHeight, out = [], seen = [], root = document.documentElement;
  const label = (el) => `${el.tagName.toLowerCase()}${el.id ? `#${el.id}` : ''}${el.classList.length ? `.${[...el.classList].join('.')}` : ''} "${(el.textContent || el.getAttribute('alt') || '').trim().slice(0, 24)}"`;
  if (root.scrollWidth > W + 1) out.push(`the page scrolls sideways (${root.scrollWidth}px content in a ${W}px viewport)`);
  const scrolls = (el) => { for (let p = el.parentElement; p && p !== document.body; p = p.parentElement) { const o = getComputedStyle(p); if (/auto|scroll/.test(o.overflowX + o.overflowY)) return true; } return false; };
  for (const el of document.body.querySelectorAll('*')) {
    if (el.tagName === 'CANVAS' || !el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })) continue;
    const ownText = [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim());
    if (!ownText && !el.matches('button, a, input, select, textarea, img, svg')) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1 || scrolls(el)) continue;
    // the ink, not the box: a full-width block holding a short line must not "overlap" its neighbour
    const ink = ownText ? [...el.childNodes].filter((n) => n.nodeType === 3 && n.textContent.trim()).flatMap((n) => { const g = document.createRange(); g.selectNodeContents(n); return [...g.getClientRects()]; }) : [r];
    seen.push({ el, ink });
    if (r.left >= -1 && r.top >= -1 && r.right <= W + 1 && r.bottom <= H + 1) continue;
    out.push(`${label(el)} at ${Math.round(r.left)},${Math.round(r.top)} ${Math.round(r.width)}x${Math.round(r.height)} is outside the ${W}x${H} viewport`);
  }
  // text drawn over other text (a hint over a translation, a toast over a name tag)
  const cover = (a, b) => { const x = Math.min(a.right, b.right) - Math.max(a.left, b.left), y = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top); return x > 3 && y > 3 ? (x * y) / Math.min(a.width * a.height, b.width * b.height) : 0; };
  for (let i = 0; i < seen.length; i++) for (let j = i + 1; j < seen.length; j++) {
    const A = seen[i], B = seen[j];
    if (A.el.contains(B.el) || B.el.contains(A.el)) continue;
    if (A.ink.some((a) => B.ink.some((b) => cover(a, b) > 0.15))) out.push(`${label(A.el)} overlaps ${label(B.el)}`);
  }
  return out.slice(0, 8);
};
const checkLayout = async (page, label) => { for (const p of await page.evaluate(LAYOUT)) problems.push(`[${label}] layout: ${p}`); };

// Plays G.demo (perfect route or learner) logic-only until it ends or the budget runs out.
// One step at a time, so frames and game seconds are exact where the run ends; with motion it
// keeps every G.motion() sample.
const PLAY_DEMO = ({ budget, motion }) => {
  const G = window.G;
  if (!G.demo) throw new Error('this page has no G.demo autoplay (see the starter src/autoplay.js)');
  if (motion && typeof G.motion !== 'function') throw new Error('--motion: this page has no G.motion() (see the starter: motion.js sample())');
  G.demo.start(); let frames = 0; const samples = motion ? [] : null;
  while (G.demo.running && frames < budget) {
    G.upd(1); frames += 1;
    if (motion) samples.push(G.motion());
  }
  return { frames, finished: !G.demo.running, samples };
};

// Lints one run's samples; findings become problems, the summary goes in the report.
function motionReport(samples, label) {
  if (!samples) return undefined;
  const found = lintMotion(samples);
  for (const f of found.slice(0, 12)) problems.push(`[${label}] motion: ${f.kind} ${f.id} steps ${f.from}-${f.to} (${(f.from / 60).toFixed(2)}-${(f.to / 60).toFixed(2)} s) peak ${f.peak}`);
  if (found.length > 12) problems.push(`[${label}] motion: ...and ${found.length - 12} more`);
  return { steps: samples.length, actors: [...new Set(samples.flat().map((s) => s.id))], findings: found.length };
}

async function checkOnce() {
  const page = await openGame();
  const result = await page.evaluate(async ({ body, demoBudget, posterAt, PLAY, motion }) => {
    const G = window.G; G.paused = true; G.step?.(2);
    let demo = null;
    if (posterAt) {
      if (!G.demo) throw new Error('--poster: this page has no G.demo autoplay (see the starter src/autoplay.js)');
      G.demo.start(); G.upd(posterAt);
    }
    if (demoBudget) { demo = new Function(`return (${PLAY})`)()({ budget: demoBudget, motion }); G.step(1); }
    const r = await new Function('G', `return (async () => { ${body} })()`)(G);
    G.render?.();   // draw the final state: logic-only G.upd leaves the last frame stale
    return { result: r ?? null, demo, state: G.state?.() ?? null, errors: G.errors };
  }, { body: script, demoBudget, posterAt, PLAY: PLAY_DEMO.toString(), motion });
  if (result.demo?.samples) { result.demo.motion = motionReport(result.demo.samples, `${device.name} demo`); delete result.demo.samples; }
  const shot = shotFor(device);
  if (shot) await screenshot(page, shot);
  await checkLayout(page, device.name);
  await page.close();
  if (posterAt) {
    const sha256 = crypto.createHash('sha256').update(fs.readFileSync(shot)).digest('hex');
    const { width, height } = device.viewport;
    fs.writeFileSync(`${shot}.json`, JSON.stringify({ method: 'demo-frames', frames: posterAt, size: `${width}x${height}`, device: device.name, url, sha256, state: result.state }, null, 2) + '\n');
    result.poster = { frames: posterAt, sha256 };
  }
  if (result.demo && !result.demo.finished) problems.push(`demo still running after ${result.demo.frames} frames: its plan() never reaches an end`);
  if (result.errors?.length) problems.push(...result.errors.map((e) => `G.errors: ${e}`));
  return result;
}

// One fresh page per learner seed; the first run's end frame is the screenshot.
async function checkBot() {
  const out = [];
  for (let i = 0; i < runs; i++) {
    const seed = seed0 + i;
    const page = await openGame({ bot: String(botAcc), seed: String(seed) });
    const r = await page.evaluate(({ budget, PLAY, motion }) => {
      const G = window.G; G.paused = true;
      const run = new Function(`return (${PLAY})`)()({ budget, motion });
      G.render?.();
      return { ...run, state: G.state?.() ?? null, errors: G.errors };
    }, { budget, PLAY: PLAY_DEMO.toString(), motion });
    const seconds = typeof r.state?.t === 'number' ? r.state.t : +(r.frames / 60).toFixed(2);
    out.push({ seed, finished: r.finished, seconds, frames: r.frames, motion: motionReport(r.samples, `${device.name} seed ${seed}`), state: r.state });
    if (!r.finished) problems.push(`bot seed ${seed} still playing after ${r.frames} frames (mode ${r.state?.mode}): the learner is stuck, or plan() cannot recover from a wrong turn`);
    else if (timeWindow && (seconds < timeWindow[0] || seconds > timeWindow[1])) problems.push(`bot seed ${seed} took ${seconds}s, outside --time ${timeWindow.join('-')}`);
    if (r.errors?.length) problems.push(...r.errors.map((e) => `G.errors (seed ${seed}): ${e}`));
    if (i === 0 && shotFor(device)) await screenshot(page, shotFor(device));
    await checkLayout(page, `${device.name} seed ${seed}`);
    await page.close();
  }
  const times = out.filter((r) => r.finished).map((r) => r.seconds);
  return { bot: { accuracy: botAcc, runs: out, seconds: times.length ? { min: Math.min(...times), max: Math.max(...times) } : null } };
}

try {
  const report = {};
  for (device of devices) report[device.name] = botAcc ? await checkBot() : await checkOnce();
  // one device prints its result as before; several print one entry per device
  console.log(JSON.stringify(devices.length > 1 ? report : report[devices[0].name], null, 2));
  if (external.length) problems.push(`external requests (a shipped game must make none): ${[...new Set(external)].join(', ')}`);
} catch (e) {
  problems.push(`check failed: ${e.message}`);
} finally {
  await browser.close();
}
if (warnings.length) console.warn(`warnings (non-fatal):\n  ${[...new Set(warnings)].join('\n  ')}`);
if (problems.length) { console.error(problems.join('\n')); process.exit(1); }
console.log(`ok${shotArg ? ` -> ${devices.map(shotFor).join(', ')}` : ''}`);
