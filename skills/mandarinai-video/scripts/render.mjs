/**
 * render.mjs — single-file HTML animation -> MP4, on this machine.
 *
 * Usage:
 *   node scripts/render.mjs [options] scene1.html [scene2.html ...]
 *     -o <out.mp4>   output path (default ./video.mp4)
 *     -d <sec|auto>  duration override (default: data-duration or legacy probe)
 *     -f <fps>       frames per second (default 30)
 *     -s <WxH>       resolution (default 1920x1080)
 *     -c <mode>      capture: "frames" (deterministic, default) | "screencast"
 *     --browser <path>  Chromium/Chrome executable (default Playwright Chromium)
 *     --overwrite       replace an existing output file
 *
 * Multiple scenes render individually and are concatenated with ffmpeg.
 * Requires: playwright (npm install in this skill dir) + ffmpeg on PATH.
 *
 * Scene preparation (ported from nexu-io/html-video adapter-hyperframes,
 * Apache-2.0): freeze all CSS animations before parse, wait for web fonts,
 * probe the real animation length (CSS keyframes + finite GSAP tweens),
 * unfreeze as the animation's t=0.
 *
 * Capture modes:
 *   frames      if window.renderAt(seconds) exists, await an explicit seek
 *               for each frame at i/fps; data-duration supplies scene length.
 *               Otherwise pause Chromium's virtual time at t=0, then per frame:
 *               screenshot, advance the clock by exactly 1/fps. CSS, GSAP,
 *               and rAF animations all follow the virtual clock, so renders
 *               are frame-exact regardless of machine load (not bit-exact:
 *               animation sampling keeps a sub-frame ±16ms phase per run).
 *               Does not drive <video>/<audio> playback — use screencast.
 *   screencast  real-time Playwright webm recording, then trim/pad. Timing
 *               is wall-clock (can jitter under load) but plays live media.
 */

import { mkdtemp, readdir, rm, writeFile, mkdir, copyFile } from 'node:fs/promises';
import { constants, existsSync, statSync } from 'node:fs';
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
let capture = 'frames';
let browserPath;
let overwrite = false;
const usage = `usage: node scripts/render.mjs [options] scene1.html [scene2.html ...]
  -o <out.mp4>   output path (default ./video.mp4)
  -d <sec|auto>  per-scene duration; otherwise data-duration or legacy probe (default auto, max 120s)
  -f <fps>       frames per second: integer 1–120 (default 30)
  -s <WxH>       positive, even resolution (default 1920x1080)
  -c <mode>      capture: "frames" (deterministic, default) | "screencast" (for <video>/<audio> scenes)
  --browser <path>  Chromium/Chrome executable (default Playwright Chromium)
  --overwrite       replace an existing output file
  --                treat remaining arguments as scene paths`;
function argumentError(message) {
  console.error(`error: ${message}\n${usage}`);
  process.exit(1);
}
let positionalOnly = false;
for (let i = 0; i < argv.length; i++) {
  const a = argv[i];
  if (positionalOnly) { scenes.push(resolve(a)); continue; }
  const next = () => {
    const v = argv[++i];
    if (v === undefined || v.startsWith('-') || !v.trim()) argumentError(`missing value for ${a}`);
    return v;
  };
  if (a === '--') positionalOnly = true;
  else if (a === '-o') outPath = next();
  else if (a === '-d') duration = next();
  else if (a === '-f') {
    const value = next();
    fps = Number(value);
    if (!/^\d+$/.test(value) || !Number.isInteger(fps) || fps < 1 || fps > 120) argumentError('-f expects an integer from 1 to 120');
  } else if (a === '-s') {
    const value = next();
    const match = /^(\d+)x(\d+)$/.exec(value);
    if (!match) argumentError('-s expects positive, even dimensions, e.g. 1920x1080');
    width = Number(match[1]); height = Number(match[2]);
    if (![width, height].every(n => Number.isSafeInteger(n) && n > 0 && n % 2 === 0)) argumentError('-s expects positive, even dimensions');
  } else if (a === '-c') {
    capture = next();
    if (capture !== 'frames' && capture !== 'screencast') argumentError(`-c expects "frames" or "screencast", got: ${capture}`);
  } else if (a === '--browser') browserPath = resolve(next());
  else if (a === '--overwrite') overwrite = true;
  else if (a === '-h' || a === '--help') { console.log(usage); process.exit(0); }
  else if (a.startsWith('-')) argumentError(`unknown option: ${a}`);
  else scenes.push(resolve(a));
}
if (!scenes.length) argumentError('no input HTML given');
for (const s of scenes) if (!existsSync(s) || !statSync(s).isFile()) argumentError(`input is not a file: ${s}`);
if (browserPath && (!existsSync(browserPath) || !statSync(browserPath).isFile())) argumentError(`browser is not a file: ${browserPath}`);
const outAbs = resolve(outPath);
if (scenes.includes(outAbs)) argumentError('output path must differ from every input scene');
if (!overwrite && existsSync(outAbs)) argumentError(`output already exists: ${outAbs}; use --overwrite to replace it`);
const explicit = duration !== 'auto';
let explicitSec = 0;
if (explicit) {
  const n = Number(duration);
  if (!Number.isFinite(n) || n <= 0) argumentError(`-d expects positive seconds or "auto", got: ${duration}`);
  explicitSec = Math.min(120, n);
}

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

// Open a scene, freeze animations through load, wait for fonts, probe length.
// Everything here runs on the real clock; the caller decides how to capture.
async function openScene(browser, htmlPath, recordDir) {
  const context = await browser.newContext({
    viewport: { width, height },
    deviceScaleFactor: 1,
    ...(recordDir ? { recordVideo: { dir: recordDir, size: { width, height } } } : {}),
  });
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(`page error: ${error.message}`));
  page.on('console', message => {
    if (message.type() === 'error') errors.push(`console error: ${message.text()}`);
  });
  page.on('requestfailed', request => {
    if (['script', 'stylesheet', 'image', 'font'].includes(request.resourceType())) {
      errors.push(`failed ${request.resourceType()}: ${request.url()} (${request.failure()?.errorText})`);
    }
  });
  const assertHealthy = () => {
    if (errors.length) throw new Error(`scene failed: ${htmlPath}\n${[...new Set(errors)].slice(0, 6).join('\n')}`);
  };

  try {
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

    // DOMContentLoaded does not guarantee images have loaded. Decode them before
    // the first frame and report missing assets instead of encoding empty scenes.
    await page.evaluate(async () => {
      await Promise.all([...document.images].map(async img => {
        if (!img.complete) {
          await new Promise((resolve, reject) => {
            const finish = () => { clearTimeout(timer); img.removeEventListener('load', finish); img.removeEventListener('error', finish); resolve(); };
            const timer = setTimeout(() => {
              img.removeEventListener('load', finish); img.removeEventListener('error', finish);
              reject(new Error(`image load timed out: ${img.currentSrc || img.src}`));
            }, 10000);
            img.addEventListener('load', finish, { once: true });
            img.addEventListener('error', finish, { once: true });
          });
        }
        if (!img.naturalWidth) throw new Error(`broken image: ${img.currentSrc || img.src || '(empty src)'}`);
        if (img.decode) await img.decode();
      }));
    });
    assertHealthy();

    const authored = await page.evaluate(() => ({
      seekable: typeof window.renderAt === 'function',
      duration: document.querySelector('[data-duration]')?.getAttribute('data-duration') ?? null,
    }));
    let authoredSec;
    if (!explicit && authored.duration !== null) {
      const value = Number(authored.duration);
      if (!Number.isFinite(value) || value <= 0) throw new Error(`invalid data-duration in ${htmlPath}: expected positive seconds, got ${JSON.stringify(authored.duration)}`);
      authoredSec = Math.min(120, value);
    }

    // Probe the real animation length: longest finite CSS animation
    // (duration+delay, skipping infinite background loops) and longest finite
    // GSAP tween if gsap is on the page.
    let totalSec = explicit ? explicitSec : (authoredSec ?? 5);
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
      if (!explicit && authoredSec === undefined && needed > totalSec) totalSec = needed;
    } catch { /* keep fallback duration */ }

    return { context, page, totalSec, seekable: authored.seekable, assertHealthy };
  } catch (error) {
    await context.close().catch(() => {});
    throw error;
  }
}

// Drive paused GSAP master timelines (multi-composition convention), then
// release the CSS freeze — this moment is the animation's true t=0.
function startAnimations(page) {
  return page.evaluate(() => {
    const tls = window.__timelines || {};
    for (const k of Object.keys(tls)) if (typeof tls[k]?.play === 'function') tls[k].play(0);
    window.__avUnfreeze?.();
  });
}

// Authored scenes own their state: seek exactly to i/fps and await two paints.
// Legacy scenes retain Chromium's virtual clock for CSS, GSAP and rAF playback.
async function renderSceneFrames(browser, htmlPath, mp4Path) {
  const { context, page, totalSec, seekable, assertHealthy } = await openScene(browser, htmlPath);
  let enc;
  let encDone;
  const capTimeout = async (promise) => {
    let timer;
    try {
      return await Promise.race([promise, new Promise((_, reject) => {
        timer = setTimeout(() => reject(new Error('frame capture stalled — check renderAt or retry media scenes with -c screencast')), 15000);
      })]);
    } finally { clearTimeout(timer); }
  };
  try {
    const cdp = await context.newCDPSession(page);
    // Device metrics belong to a CDP session. A fresh capture session must set
    // its own override: otherwise Chrome can capture at its native window size
    // and restore that size over Playwright's emulated viewport afterward.
    await cdp.send('Emulation.setDeviceMetricsOverride', {
      width, height, deviceScaleFactor: 1, mobile: false,
      screenWidth: width, screenHeight: height,
    });
    const assertViewport = async () => {
      const actual = await page.evaluate(() => ({ width: innerWidth, height: innerHeight, scale: devicePixelRatio }));
      if (actual.width !== width || actual.height !== height || actual.scale !== 1) {
        throw new Error(`capture viewport changed: expected ${width}x${height} @ 1x, got ${actual.width}x${actual.height} @ ${actual.scale}x`);
      }
    };
    await assertViewport();
    if (!seekable) {
      await cdp.send('Emulation.setVirtualTimePolicy', { policy: 'pause' });
      await startAnimations(page);
    }

    const nFrames = Math.max(1, Math.round(totalSec * fps));
    process.stderr.write(`  capturing ${nFrames} frames (${totalSec.toFixed(3)}s @ ${fps}fps, ${seekable ? 'renderAt seeks' : 'virtual time'})...\n`);

    enc = spawn('ffmpeg', [
      '-y', '-f', 'image2pipe', '-framerate', String(fps), '-i', '-',
      '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-preset', 'medium', '-crf', '20',
      '-movflags', '+faststart',
      mp4Path,
    ], { stdio: ['pipe', 'ignore', 'pipe'] });
    enc.stdin.on('error', () => {}); // encDone reports an encoder failure.
    let encErr = '';
    enc.stderr.on('data', chunk => encErr += chunk);
    encDone = new Promise((resolve, reject) => {
      enc.on('error', error => reject(error.code === 'ENOENT' ? new Error('ffmpeg not found: brew install ffmpeg') : error));
      enc.on('exit', code => code === 0 ? resolve() : reject(new Error(`ffmpeg exited ${code}: ${encErr.slice(-1500)}`)));
    });
    // Observe early encoder failure while an in-flight browser call is pending.
    encDone.catch(() => {});

    const frameBudget = 1000 / fps;
    for (let i = 0; i < nFrames; i++) {
      if (seekable) {
        await capTimeout(page.evaluate(async seconds => {
          await window.renderAt(seconds);
          await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
        }, i / fps));
      }
      assertHealthy();
      await assertViewport();
      const { data } = await capTimeout(cdp.send('Page.captureScreenshot', {
        format: 'png', fromSurface: true, captureBeyondViewport: false,
        clip: { x: 0, y: 0, width, height, scale: 1 },
      }));
      await assertViewport();
      assertHealthy();
      if (!enc.stdin.write(Buffer.from(data, 'base64'))) {
        await capTimeout(Promise.race([
          new Promise(resolve => enc.stdin.once('drain', resolve)),
          encDone.then(() => { throw new Error('ffmpeg ended before all frames were written'); }),
        ]));
      }
      if (!seekable && i < nFrames - 1) {
        await capTimeout(Promise.all([
          new Promise(resolve => cdp.once('Emulation.virtualTimeBudgetExpired', resolve)),
          cdp.send('Emulation.setVirtualTimePolicy', { policy: 'advance', budget: frameBudget }),
        ]));
      }
    }
    assertHealthy();
    enc.stdin.end();
    await encDone;
    return nFrames / fps;
  } catch (error) {
    enc?.stdin.destroy();
    enc?.kill('SIGKILL');
    await encDone?.catch(() => {});
    throw error;
  } finally {
    await context.close().catch(() => {});
  }
}

// Real-time capture: Playwright webm screencast, then trim/pad with ffmpeg.
// Wall-clock timing (can jitter under load) but drives <video>/<audio>.
async function renderSceneScreencast(browser, htmlPath, mp4Path) {
  const recordDir = await mkdtemp(join(tmpdir(), 'av-rec-'));
  let context;
  try {
    const opened = await openScene(browser, htmlPath, recordDir);
    const { page, totalSec, assertHealthy } = opened;
    context = opened.context;
    await startAnimations(page);

    process.stderr.write(`  recording ${totalSec.toFixed(1)}s @ ${fps}fps...\n`);
    try {
      await page.waitForTimeout(Math.round(totalSec * 1000));
      assertHealthy();
    } finally {
      await context.close();
    }

    const webms = (await readdir(recordDir)).filter(f => f.endsWith('.webm')).sort();
    if (!webms.length) throw new Error('playwright produced no webm');
    const webm = join(recordDir, webms[webms.length - 1]);

    // Keep the LAST totalSec of the webm. Playwright only emits frames when the
    // page paints, so the webm's internal timeline is shorter than wall clock
    // during page load (a slow CDN can stall paints for seconds) — wall-clock
    // lead-in trimming over-seeks. The CSS freeze guarantees everything before
    // unfreeze is a still first frame, so the recording window we waited for is
    // exactly the tail of the file.
    // tpad always: a scene that never repaints (static frame) yields a webm far
    // shorter than totalSec, and -t alone cannot extend it — clone the last
    // frame out to the target length, then cut.
    const webmSec = await ffprobeDuration(webm).catch(() => 0);
    const seekSec = webmSec > totalSec + 0.15 ? Math.max(0, webmSec - totalSec - 0.1) : 0;
    await ffmpeg([
      '-y',
      ...(seekSec > 0 ? ['-ss', seekSec.toFixed(3)] : []),
      '-i', webm,
      '-vf', `tpad=stop_mode=clone:stop_duration=${totalSec}`,
      '-t', String(totalSec),
      '-r', String(fps),
      '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-preset', 'medium', '-crf', '20',
      '-movflags', '+faststart',
      mp4Path,
    ]);
    return totalSec;
  } finally {
    await context?.close().catch(() => {});
    await rm(recordDir, { recursive: true, force: true }).catch(() => {});
  }
}

const renderScene = capture === 'screencast' ? renderSceneScreencast : renderSceneFrames;

// ---------- main ----------
await mkdir(dirname(outAbs), { recursive: true });
// Render into a unique directory, then publish only a completed MP4. COPYFILE_EXCL
// also protects against another process creating the destination during capture.
const workDir = await mkdtemp(join(tmpdir(), 'av-render-'));
let browser;
try {
  // Legacy frames mode needs these flags for virtual-time compositor sampling.
  browser = await chromium.launch({
    headless: true,
    ...(browserPath ? { executablePath: browserPath } : {}),
    args: [
      '--no-sandbox',
      ...(capture === 'frames' ? [
        '--run-all-compositor-stages-before-draw',
        '--disable-new-content-rendering-timeout',
        '--disable-threaded-animation',
        '--disable-threaded-scrolling',
        '--disable-checker-imaging',
        '--disable-image-animation-resync',
        '--disable-gpu',
      ] : []),
    ],
  });
  const resultPath = join(workDir, 'result.mp4');
  let total = 0;
  if (scenes.length === 1) {
    total = await renderScene(browser, scenes[0], resultPath);
  } else {
    const parts = [];
    for (let i = 0; i < scenes.length; i++) {
      process.stderr.write(`scene ${i + 1}/${scenes.length}: ${scenes[i]}\n`);
      const part = join(workDir, `part-${String(i).padStart(2, '0')}.mp4`);
      total += await renderScene(browser, scenes[i], part);
      parts.push(part);
    }
    const listPath = join(workDir, 'list.txt');
    await writeFile(listPath, parts.map(path => `file '${path}'`).join('\n'));
    await ffmpeg(['-y', '-f', 'concat', '-safe', '0', '-i', listPath, '-c', 'copy', resultPath]);
  }
  await copyFile(resultPath, outAbs, overwrite ? 0 : constants.COPYFILE_EXCL);
  console.log(`MP4: ${outAbs} (${scenes.length > 1 ? `${scenes.length} scenes, ` : ''}${total.toFixed(3)}s)`);
} catch (error) {
  console.error(`error: ${error.message}`);
  process.exitCode = 1;
} finally {
  await browser?.close().catch(() => {});
  await rm(workDir, { recursive: true, force: true }).catch(() => {});
}
