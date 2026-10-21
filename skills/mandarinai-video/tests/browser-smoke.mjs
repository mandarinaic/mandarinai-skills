// Optional integration checks: node --test tests/browser-smoke.mjs
// Set MANDARIN_VIDEO_BROWSER to use an installed Chrome executable.
import { test, after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, writeFile, rm } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { chromium } from 'playwright';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const work = await mkdtemp(join(tmpdir(), "mandarinai browser's test "));
const executablePath = process.env.MANDARIN_VIDEO_BROWSER;
const browserArgs = executablePath ? ['--browser', executablePath] : [];
after(() => rm(work, { recursive: true, force: true }));
const run = (file, args) => execFileSync(file, args, { cwd: root, timeout: 45000, maxBuffer: 8 * 1024 * 1024 });

test('authored capture preserves CSS viewport, exact frames, and backwards seek', async () => {
  const html = join(work, 'seek scene.html');
  const mp4 = join(work, 'seek.mp4');
  await writeFile(html, `<!doctype html><html data-duration="0.4"><meta name="viewport" content="width=device-width,initial-scale=1">
  <style>html,body{margin:0;width:100%;height:100%}#marker{position:absolute;left:25vw;width:25vw;top:0;bottom:0;background:#00ff00}</style>
  <div id="marker"></div><script>window.renderAt=async t=>{await Promise.resolve();if(innerWidth!==320||innerHeight!==568)throw Error('wrong viewport');document.body.style.background=t<.15?'#ff0000':'#0000ff'};window.renderAt(.4);</script></html>`);
  run('node', ['scripts/render.mjs', ...browserArgs, '-s', '320x568', '-f', '10', '-o', mp4, html]);
  const probe = JSON.parse(run('ffprobe', ['-v', 'error', '-show_streams', '-of', 'json', mp4])).streams[0];
  assert.equal(probe.width, 320);
  assert.equal(probe.height, 568);
  assert.equal(Number(probe.nb_frames), 4);
  const pixels = run('ffmpeg', ['-v', 'error', '-i', mp4, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']);
  const pixel = (frame, x) => [...pixels.subarray(((frame * 568 + 284) * 320 + x) * 3, ((frame * 568 + 284) * 320 + x) * 3 + 3)];
  const first = pixel(0, 10), last = pixel(3, 10), marker = pixel(3, 90);
  assert.ok(first[0] > 200 && first[2] < 50, `initial seek: ${first}`);
  assert.ok(last[2] > 200 && last[0] < 50, `final seek: ${last}`);
  assert.ok(marker[1] > 200 && marker[0] < 50, `25vw marker: ${marker}`);
  const original = await readFile(mp4);
  assert.throws(() => run('node', ['scripts/render.mjs', '-o', mp4, html]));
  assert.deepEqual(await readFile(mp4), original);
});

test('legacy virtual-time CSS still animates through its final frame', async () => {
  const html = join(work, 'legacy.html'), mp4 = join(work, 'legacy.mp4');
  await writeFile(html, '<!doctype html><style>html,body{margin:0;width:100%;height:100%}body{animation:color .2s forwards}@keyframes color{from{background:#f00}to{background:#00f}}</style>');
  run('node', ['scripts/render.mjs', ...browserArgs, '-s', '160x90', '-f', '10', '-d', '.4', '-o', mp4, html]);
  const pixels = run('ffmpeg', ['-v', 'error', '-i', mp4, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']);
  assert.equal(pixels.length, 160 * 90 * 3 * 4);
  assert.ok(pixels[0] > 200 && pixels[2] < 50);
  const end = 160 * 90 * 3 * 3;
  assert.ok(pixels[end + 2] > 200 && pixels[end] < 50);
});

test('file preview can seek its opaque-origin iframe without page errors', async () => {
  const source = join(work, 'source.json'), brief = join(work, 'brief.json'), project = join(work, 'project');
  run('python3', ['scripts/prepare-content.py', '--kind', 'word', '--id', '900001', '--input', 'examples/sources/word.json', '--out', source]);
  await writeFile(brief, JSON.stringify({ source, mode: 'tutorial', width: 320, height: 568, scenes: [
    { layout: 'lesson', heading: '学习', text: '学习', pinyin: ['xué', 'xí'], duration: 2 },
  ] }));
  run('python3', ['scripts/build-project.py', brief, '--out', project]);
  const browser = await chromium.launch({ headless: true, ...(executablePath ? { executablePath } : {}), args: ['--no-sandbox'] });
  try {
    const page = await browser.newPage({ viewport: { width: 1200, height: 900 } });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(pathToFileURL(join(project, 'preview.html')).href);
    const scene = page.frameLocator('iframe');
    await scene.locator('.heading').waitFor();
    await page.locator('#seek').evaluate(el => { el.value = '.25'; el.dispatchEvent(new Event('input')); });
    await scene.locator('.progress span').evaluate(async el => {
      for (let i = 0; i < 30; i++) {
        if (el.style.transform === 'scaleX(0.125)') return;
        await new Promise(resolve => requestAnimationFrame(resolve));
      }
      throw Error('preview did not seek to .25 seconds');
    });
    assert.deepEqual(errors, []);
  } finally { await browser.close(); }
});
