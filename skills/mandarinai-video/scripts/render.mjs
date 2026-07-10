/**
 * render.mjs — single-file HTML animation -> MP4, on this machine.
 *
 * Usage:
 *   node scripts/render.mjs [options] scene1.html [scene2.html ...]
 *     -o <out.mp4>   output path (default ./video.mp4)
 *     -d <sec|auto>  per-scene duration; "auto" probes the animation length (default auto)
 *     -f <fps>       frames per second (default 30)
 *     -s <WxH>       resolution (default 1920x1080)
 *
 * Multiple scenes render individually and are concatenated with ffmpeg.
 * Requires: playwright (npm install in this skill dir) + ffmpeg on PATH.
 *
 * Recording strategy (ported from nexu-io/html-video adapter-hyperframes,
 * Apache-2.0): freeze all CSS animations before parse, wait for web fonts,
 * probe the real animation length (CSS keyframes + finite GSAP tweens),
 * unfreeze as recording t=0, then trim the dead lead-in and encode.
 */

import { mkdtemp, readdir, rm, writeFile, mkdir } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { spawn } from 'node:child_process';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

// ---------- args ----------
const argv = process.argv.slice(2);
const scenes = [];
let outPath = 'video.mp4';
let duration = 'auto';
let fps = 30;
let width = 1920, height = 1080;
for (let i = 0; i < argv.length; i++) {
  const a = argv[i];
  if (a === '-o') outPath = argv[++i];
  else if (a === '-d') duration = argv[++i];
  else if (a === '-f') fps = Number(argv[++i]) || 30;
  else if (a === '-s') { const m = /^(\d+)x(\d+)$/.exec(argv[++i] || ''); if (m) { width = +m[1]; height = +m[2]; } }
  else if (a === '-h' || a === '--help') { console.log('see header of this file'); process.exit(0); }
  else scenes.push(resolve(a));
}
if (!scenes.length) { console.error('error: no input HTML given'); process.exit(1); }
for (const s of scenes) if (!existsSync(s)) { console.error(`error: not found: ${s}`); process.exit(1); }
const explicit = duration !== 'auto';
const explicitSec = explicit ? Math.max(0.5, Number(duration)) : 0;

const { chromium } = await import('playwright').catch(() => {
  console.error('error: playwright not installed. Run in this skill dir: npm install && npx playwright install chromium');
  process.exit(1);
});

function ffmpeg(args) {
  return new Promise((res, rej) => {
    const p = spawn('ffmpeg', args, { stdio: ['ignore', 'ignore', 'pipe'] });
    let err = '';
    p.stderr.on('data', c => err += c);
    p.on('error', e => rej(e.code === 'ENOENT' ? new Error('ffmpeg not found: brew install ffmpeg') : e));
    p.on('exit', c => c === 0 ? res() : rej(new Error(`ffmpeg exited ${c}: ${err.slice(-1500)}`)));
  });
}

function ffprobeDuration(path) {
  return new Promise((res, rej) => {
    const p = spawn('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path], { stdio: ['ignore', 'pipe', 'pipe'] });
    let out = '';
    p.stdout.on('data', c => out += c);
    p.on('error', e => rej(e.code === 'ENOENT' ? new Error('ffprobe not found: brew install ffmpeg') : e));
    p.on('exit', c => c === 0 ? res(parseFloat(out) || 0) : rej(new Error('ffprobe failed')));
  });
}

async function renderScene(browser, htmlPath, mp4Path) {
  const recordDir = await mkdtemp(join(tmpdir(), 'av-rec-'));
  const context = await browser.newContext({
    viewport: { width, height },
    deviceScaleFactor: 1,
    recordVideo: { dir: recordDir, size: { width, height } },
  });
  const page = await context.newPage();

  // Freeze every CSS animation before the document parses, so nothing plays
  // during page load / font fetch. Unfreezing later is the animation's t=0.
  await page.addInitScript(() => {
    const style = document.createElement('style');
    style.id = '__av_freeze';
    style.textContent = '*, *::before, *::after { animation-play-state: paused !important; }';
    const attach = () => (document.head || document.documentElement).appendChild(style);
    if (document.head || document.documentElement) attach();
    else document.addEventListener('DOMContentLoaded', attach, { once: true });
    window.__avUnfreeze = () => document.getElementById('__av_freeze')?.remove();
  });

  await page.goto(pathToFileURL(htmlPath).href, { waitUntil: 'domcontentloaded' });

  // Wait for web fonts: stylesheet <link>s first (they register @font-face),
  // then force-load each face, then fonts.ready. Capped so a blocked CDN
  // can't stall the render.
  await page.evaluate(() => new Promise((done) => {
    const fonts = document.fonts;
    if (!fonts?.ready?.then) return done();
    let settled = false;
    const finish = () => { if (!settled) { settled = true; requestAnimationFrame(() => requestAnimationFrame(done)); } };
    const cap = setTimeout(finish, 8000);
    const links = [...document.querySelectorAll('link[rel="stylesheet"]')].map(l => {
      try { if (l.sheet?.cssRules) return Promise.resolve(); } catch { /* pending */ }
      return new Promise(r => { l.addEventListener('load', r, { once: true }); l.addEventListener('error', r, { once: true }); setTimeout(r, 6000); });
    });
    Promise.all(links)
      .then(() => { const loads = []; fonts.forEach(f => { try { loads.push(f.load().catch(() => {})); } catch { /* pre-paint */ } }); return Promise.all(loads); })
      .then(() => fonts.ready)
      .then(() => { clearTimeout(cap); finish(); })
      .catch(() => { clearTimeout(cap); finish(); });
  })).catch(() => {});
  await page.waitForTimeout(100);

  // Probe the real animation length: longest finite CSS animation
  // (duration+delay, skipping infinite background loops) and longest finite
  // GSAP tween if gsap is on the page.
  let totalSec = explicit ? explicitSec : 5;
  try {
    const animMs = await page.evaluate(() => {
      let max = 0;
      for (const el of document.querySelectorAll('*')) {
        const s = getComputedStyle(el);
        const durs = (s.animationDuration || '').split(',');
        const dels = (s.animationDelay || '').split(',');
        const iters = (s.animationIterationCount || '').split(',');
        durs.forEach((d, i) => {
          if ((iters[i] || '').trim() === 'infinite') return;
          max = Math.max(max, ((parseFloat(d) || 0) + (parseFloat(dels[i] || '0') || 0)) * 1000);
        });
      }
      let gsapMs = 0;
      const children = window.gsap?.globalTimeline?.getChildren?.(true, true, true) ?? [];
      for (const c of children) {
        const repeat = typeof c.repeat === 'function' ? c.repeat() : (c.vars?.repeat ?? 0);
        if (repeat === -1) continue;
        const td = typeof c.totalDuration === 'function' ? c.totalDuration() : 0;
        if (Number.isFinite(td)) gsapMs = Math.max(gsapMs, td * 1000);
      }
      return Math.max(max, gsapMs);
    });
    const needed = Math.min(30, (animMs + 400) / 1000);
    if (!explicit && needed > totalSec) totalSec = needed;
  } catch { /* keep fallback duration */ }

  // Drive paused GSAP master timelines (multi-composition convention), then
  // release the CSS freeze — this moment is the animation's true t=0.
  await page.evaluate(() => {
    const tls = window.__timelines || {};
    for (const k of Object.keys(tls)) if (typeof tls[k]?.play === 'function') tls[k].play(0);
    window.__avUnfreeze?.();
  }).catch(() => {});

  process.stderr.write(`  recording ${totalSec.toFixed(1)}s @ ${fps}fps...\n`);
  await page.waitForTimeout(Math.round(totalSec * 1000));
  await context.close();

  const webms = (await readdir(recordDir)).filter(f => f.endsWith('.webm')).sort();
  if (!webms.length) throw new Error('playwright produced no webm');
  const webm = join(recordDir, webms[webms.length - 1]);

  // Keep the LAST totalSec of the webm. Playwright only emits frames when the
  // page paints, so the webm's internal timeline is shorter than wall clock
  // during page load (a slow CDN can stall paints for seconds) — wall-clock
  // lead-in trimming over-seeks. The CSS freeze guarantees everything before
  // unfreeze is a still first frame, so the recording window we waited for is
  // exactly the tail of the file.
  const webmSec = await ffprobeDuration(webm).catch(() => 0);
  const seekSec = webmSec > totalSec + 0.15 ? Math.max(0, webmSec - totalSec - 0.1) : 0;
  await ffmpeg([
    '-y',
    ...(seekSec > 0 ? ['-ss', seekSec.toFixed(3)] : []),
    '-i', webm,
    ...(explicit ? ['-vf', `tpad=stop_mode=clone:stop_duration=${totalSec}`] : []),
    '-t', String(totalSec),
    '-r', String(fps),
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-preset', 'medium', '-crf', '20',
    '-movflags', '+faststart',
    mp4Path,
  ]);
  await rm(recordDir, { recursive: true, force: true }).catch(() => {});
  return totalSec;
}

// ---------- main ----------
const outAbs = resolve(outPath);
await mkdir(dirname(outAbs), { recursive: true });
const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
try {
  if (scenes.length === 1) {
    const sec = await renderScene(browser, scenes[0], outAbs);
    console.log(`MP4: ${outAbs} (${sec.toFixed(1)}s)`);
  } else {
    const workDir = await mkdtemp(join(tmpdir(), 'av-concat-'));
    const parts = [];
    let total = 0;
    for (let i = 0; i < scenes.length; i++) {
      process.stderr.write(`scene ${i + 1}/${scenes.length}: ${scenes[i]}\n`);
      const part = join(workDir, `part-${String(i).padStart(2, '0')}.mp4`);
      total += await renderScene(browser, scenes[i], part);
      parts.push(part);
    }
    const listPath = join(workDir, 'list.txt');
    await writeFile(listPath, parts.map(p => `file '${p}'`).join('\n'));
    await ffmpeg(['-y', '-f', 'concat', '-safe', '0', '-i', listPath, '-c', 'copy', outAbs]);
    await rm(workDir, { recursive: true, force: true }).catch(() => {});
    console.log(`MP4: ${outAbs} (${scenes.length} scenes, ~${total.toFixed(1)}s)`);
  }
} finally {
  await browser.close().catch(() => {});
}
