// End to end: scaffold -> serve -> full story loop -> pack -> full loop again from file://.
// Needs the source cast models (MANDARINAI_CAST_3D or ~/Downloads/3D/final); skips without them.
// Run from the skill root: node --test tests/
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn, execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const SKILL = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const SRC = process.env.MANDARINAI_CAST_3D || path.join(os.homedir(), 'Downloads/3D/final');
const haveCast = fs.existsSync(path.join(SRC, 'rat.glb')) && fs.existsSync(path.join(SRC, 'ox.glb'));
const STEPS = path.join(SKILL, 'tests/full-loop.steps.js');
const node = (args) => execFileSync(process.execPath, args, { cwd: SKILL, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
const result = (stdout) => JSON.parse(stdout.slice(stdout.indexOf('{'), stdout.lastIndexOf('}') + 1)).result;

const expectFullLoop = (r) => {
  assert.equal(r.intro, 'talk');
  assert.equal(r.afterIntro, 'play');
  assert.ok(Math.abs(r.riverWallZ - 2.55) < 0.05, `river should stop the hero at z=2.55, got ${r.riverWallZ}`);
  assert.equal(r.ferryTalk, true);
  assert.equal(r.cut, 'cut');
  assert.equal(r.crossed, true);
  assert.equal(r.words, '河快到');
  assert.equal(r.end, 'end');
};

test('starter plays start to finish in dev and as a packed single file', { skip: !haveCast && `no cast models in ${SRC}`, timeout: 240000 }, async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'mandarinai-game-'));
  const game = path.join(dir, 'zodiac');
  node(['scripts/new-game.mjs', '--out', game, '--cast', 'rat,ox']);
  const manifest = JSON.parse(fs.readFileSync(path.join(game, 'assets/cast/cast.json'), 'utf8'));
  assert.deepEqual(Object.keys(manifest).sort(), ['ox', 'rat']);
  assert.ok(manifest.rat.triangles < 25000 && Math.abs(manifest.rat.height - 1.1) < 0.01);

  const port = String(20000 + Math.floor(Math.random() * 20000));
  const server = spawn(process.execPath, [path.join(game, 'serve.mjs')], { env: { ...process.env, PORT: port }, stdio: 'ignore' });
  try {
    await new Promise((r) => setTimeout(r, 600));
    expectFullLoop(result(node(['scripts/play-check.mjs', `http://localhost:${port}/?mute`, '--script', STEPS])));
  } finally { server.kill(); }

  node(['scripts/build-single-html.mjs', game, '--name', 'zodiac']);
  const packed = path.join(game, 'dist/zodiac.html');
  assert.ok(fs.statSync(packed).size < 8e6, 'starter single file should stay small');
  expectFullLoop(result(node(['scripts/play-check.mjs', `file://${packed}?mute`, '--script', STEPS])));
  fs.rmSync(dir, { recursive: true, force: true });
});
