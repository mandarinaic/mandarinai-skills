// Optional integration checks: node --test tests/browser-smoke.mjs
// Set MANDARIN_VIDEO_BROWSER to use an installed Chrome executable.
import { test, after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, writeFile, rm, mkdir, copyFile } from 'node:fs/promises';
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


async function castFixture(name) {
  const project = join(work, name);
  await mkdir(join(project, 'scenes'), { recursive: true });
  await mkdir(join(project, 'assets', 'cast'), { recursive: true });
  for (const speaker of ['jin', 'yue']) await copyFile(join(root, 'assets', 'cast', `${speaker}-calm.webp`), join(project, 'assets', 'cast', `${speaker}-calm.webp`));
  await copyFile(join(root, 'assets', 'brand', 'mandarinai-logo.png'), join(project, 'assets', 'mandarinai-logo.png'));
  const profiles = {
    jin: { id: 'jin', name: 'Jin', hanzi: '金', role: 'Grammar mentor', portrait: 'assets/cast/jin-calm.webp' },
    yue: { id: 'yue', name: 'Yue', hanzi: '悦', role: 'Learning guide', portrait: 'assets/cast/yue-calm.webp' },
  };
  const tracks = [
    { file: 'assets/one.wav', speaker: 'jin', voice: null, start: .5, duration: .5, caption: '你想喝茶吗？' },
    { file: 'assets/two.wav', speaker: 'yue', voice: null, start: 1.5, duration: .5, caption: '我想喝茶。' },
  ];
  const data = { duration: 4, speaker: 'jin', presenter: profiles.jin, cast: profiles, voice_tracks: tracks, lines: [], timing: { bpm: 120 }, cues: { content: { seconds: .75, frame: 8, beat: 1.5 } } };
  const markup = (speaker, text, translation, start, end) => `<article class="dialogue-line" data-speaker="${speaker}" data-line-start="${start}" data-line-end="${end}"><img class="dialogue-portrait" src="../${profiles[speaker].portrait}" alt="${profiles[speaker].name}"><div><div class="speaker-name">${profiles[speaker].name}</div><p class="line-chinese">${text}</p><p class="line-translation">${translation}</p></div></article>`;
  const values = {
    DURATION: '4', TITLE: 'Cast lesson', STYLE: 'clean', LAYOUT: 'dialogue', HEADING: '想 · want to', MODE: 'Tutorial',
    LABEL: 'A short conversation', TEXT: '', TRANSLATION: '', BULLETS: '', IMAGE: '', FOOTER: 'mandarinai.com · Grammar', INDEX: '1', COUNT: '1',
    DIALOGUE_HTML: `<div class="dialogue-lines">${markup('jin', '你想喝茶吗？', 'Would you like some tea?', .5, 1)}${markup('yue', '我想喝茶。', 'I would like some tea.', 1.5, 2)}</div>`,
    PRESENTER_HTML: `<aside class="presenter-strip"><img class="presenter-portrait" src="../${profiles.jin.portrait}" alt="Jin"><div><strong class="presenter-name">Jin 金</strong><span class="presenter-role">Grammar mentor</span></div></aside>`,
    SCENE_DATA: JSON.stringify(data),
  };
  const template = (await readFile(join(root, 'assets', 'project-scene.html'), 'utf8')).replace('data-enter="0.06"', 'data-enter="0.06" data-cue="content"');
  const html = template.replace(/@@([A-Z_]+)@@/g, (_, key) => {
    assert.ok(key in values, `unknown template field ${key}`);
    return values[key];
  });
  await writeFile(join(project, 'scenes', '01.html'), html);
  return { project, profiles, tracks, data };
}

test('cast scenes seek speakers and dialogue purely, honoring visual cues across aspect ratios', async () => {
  const { project } = await castFixture('cast-ui');
  const browser = await chromium.launch({ headless: true, ...(executablePath ? { executablePath } : {}), args: ['--no-sandbox'] });
  try {
    for (const viewport of [{ width: 320, height: 568 }, { width: 640, height: 640 }, { width: 960, height: 540 }]) {
      const page = await browser.newPage({ viewport });
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.goto(pathToFileURL(join(project, 'scenes', '01.html')).href);
      await page.evaluate(() => document.fonts.ready);
      const stateAt = t => page.evaluate(t => {
        window.renderAt(t);
        return { speaker: document.querySelector('.presenter-strip').dataset.speaker,
          speaking: document.querySelector('.presenter-strip').classList.contains('is-speaking'),
          active: [...document.querySelectorAll('.dialogue-line.is-active')].map(el => el.dataset.speaker),
          past: [...document.querySelectorAll('.dialogue-line.is-past')].map(el => el.dataset.speaker),
          labelOpacity: Number(document.querySelector('.eyebrow').style.opacity),
          contentCue: window.cue('content', 0), name: document.querySelector('.presenter-name').textContent };
      }, t);
      assert.deepEqual((await stateAt(.6)).active, ['jin']);
      const pause = await stateAt(1.2);
      assert.equal(pause.speaker, 'jin');
      assert.equal(pause.speaking, false);
      assert.deepEqual(pause.active, []);
      assert.deepEqual(pause.past, ['jin']);
      assert.deepEqual((await stateAt(1.6)).active, ['yue']);
      const ending = await stateAt(3);
      assert.equal(ending.speaker, 'yue');
      assert.equal(ending.name, 'Yue 悦');
      assert.deepEqual(ending.active, []);
      assert.deepEqual((await stateAt(.6)).active, ['jin']);
      const beginning = await stateAt(.2);
      assert.equal(beginning.speaker, 'jin');
      assert.equal(beginning.labelOpacity, 0);
      assert.equal(beginning.contentCue, .75);
      assert.ok((await stateAt(1.4)).labelOpacity > .95);
      const layout = await page.evaluate(() => {
        window.renderAt(3);
        const box = selector => { const r = document.querySelector(selector).getBoundingClientRect(); return { top: r.top, bottom: r.bottom, left: r.left, right: r.right }; };
        return { line: box('.dialogue-lines'), presenter: box('.presenter-strip'), footer: box('.footer'), height: innerHeight, width: innerWidth,
          portraitsReady: [...document.querySelectorAll('img')].every(img => img.complete && img.naturalWidth > 0) };
      });
      assert.ok(layout.line.bottom <= layout.presenter.top, JSON.stringify({ viewport, layout }));
      assert.ok(layout.presenter.bottom <= layout.footer.top, JSON.stringify({ viewport, layout }));
      assert.ok(layout.footer.bottom < layout.height);
      assert.ok(layout.line.left >= 0 && layout.line.right <= layout.width);
      assert.ok(layout.portraitsReady);
      // Match render.mjs's two-paint settling before comparing pixels. A raw
      // screenshot taken directly after style changes may catch raster upload.
      const settledFrame = async t => {
        await page.evaluate(async t => {
          await window.renderAt(t);
          await Promise.all([...document.images].map(img => img.decode()));
          await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
        }, t);
        return page.screenshot();
      };
      const secondSpeaker = await settledFrame(1.6);
      await settledFrame(0);
      assert.deepEqual(await settledFrame(1.6), secondSpeaker, `speaker frame differs after backwards seek at ${viewport.width}x${viewport.height}`);
      assert.deepEqual(errors, []);
      await page.close();
    }
  } finally { await browser.close(); }
});

test('two cast voices and ducked BGM render to a verified full-length MP4', async () => {
  const { project, profiles, tracks } = await castFixture('cast-render');
  for (const [file, frequency] of [['one', 880], ['two', 1320], ['music', 220]]) {
    run('ffmpeg', ['-n', '-v', 'error', '-f', 'lavfi', '-i', `sine=frequency=${frequency}:sample_rate=48000:duration=0.5`, join(project, 'assets', `${file}.wav`)]);
  }
  const manifest = { schema_version: 1, dimensions: { width: 320, height: 568 }, fps: 10, frames: 40, duration: 4,
    audio_mode: 'narrated', cast: { presenter: 'jin', characters: profiles }, timing: { bpm: 120, beats_per_bar: 4 },
    bgm: { file: 'assets/music.wav', volume: .12 }, scenes: [{ file: 'scenes/01.html', speaker: 'jin', heading: '想', start: 0, frames: 40, duration: 4, voice_tracks: tracks }] };
  await writeFile(join(project, 'project.json'), JSON.stringify(manifest));
  const output = join(work, 'cast-film.mp4');
  run('python3', ['scripts/render-project.py', project, ...browserArgs, '--output', output]);
  const report = JSON.parse(await readFile(join(work, 'cast-film.verification.json'), 'utf8'));
  assert.equal(report.audio_codec, 'aac');
  assert.equal(report.frames, 40);
  assert.equal(report.voice_track_count, 2);
  assert.deepEqual(report.speakers, ['jin', 'yue']);
  assert.equal(report.bgm_ducked, true);
  assert.equal(report.bpm, 120);
  assert.ok(report.checks.audio_covers_full_video);
  assert.ok(Math.abs(report.audio_duration - 4) < .02);
});
