// Motion lint: per-step actor samples in, glitches out.
import test from 'node:test';
import assert from 'node:assert/strict';
import { lintMotion } from '../scripts/motion-lint.mjs';

// one actor walking along +x at 4.5 m/s, sampled every 1/60 s
const walk = (n, f = () => ({})) => Array.from({ length: n }, (_, i) => [{ id: 'hero', x: i * 0.075, y: 0, z: 0, ry: 1.2, sx: 1, sy: 1, sz: 1, placed: false, ...f(i) }]);
const kinds = (found) => found.map((x) => x.kind);

test('smooth walking is clean', () => {
  assert.deepEqual(lintMotion(walk(120)), []);
});

test('a jump impulse is not a snap', () => {
  // takeoff at 3.6 m/s under gravity: velocity changes by 0.06 m per step once
  const frames = walk(120, (i) => (i < 40 ? {} : { y: Math.max(0, 3.6 * (i - 40) / 60 - 4.9 * ((i - 40) / 60) ** 2) }));
  assert.deepEqual(lintMotion(frames), []);
});

test('a position jump is a snap, reported once with its frame range', () => {
  const found = lintMotion(walk(120, (i) => (i >= 60 ? { x: i * 0.075 + 1.5 } : {})));
  assert.deepEqual(kinds(found), ['snap']);
  assert.equal(found[0].id, 'hero');
  assert.ok(found[0].from >= 58 && found[0].to <= 61, JSON.stringify(found[0]));
});

test('a teleport marked with placed is not a snap', () => {
  const found = lintMotion(walk(120, (i) => (i >= 60 ? { x: i * 0.075 + 1.5, placed: i === 60 } : {})));
  assert.deepEqual(found, []);
});

test('turning past the ±π seam is not a spin, an instant half-turn is', () => {
  assert.deepEqual(lintMotion(walk(60, (i) => ({ ry: 3.1 + i * 0.01 }))), []);
  assert.deepEqual(kinds(lintMotion(walk(60, (i) => ({ ry: i < 30 ? 0 : Math.PI })))), ['spin']);
});

test('feet under the ground, NaN, and squash past its limits are reported', () => {
  assert.deepEqual(kinds(lintMotion(walk(30, (i) => (i >= 10 ? { y: -(i - 10) * 0.01 } : {})))), ['below-ground']);   // sinking slowly
  assert.deepEqual(kinds(lintMotion(walk(30, (i) => (i === 10 ? { x: Number.NaN } : {})))), ['nan']);
  assert.deepEqual(kinds(lintMotion(walk(30, (i) => (i >= 10 && i < 14 ? { sy: 0.5 } : {})))), ['squash']);
});

test('each actor is judged on its own, and one that appears mid-run is not a snap', () => {
  const frames = walk(80).map((fr, i) => (i >= 40 ? [...fr, { id: 'npc', x: 9, y: 0, z: 9, ry: 0, sx: 1, sy: 1, sz: 1, placed: false }] : fr));
  assert.deepEqual(lintMotion(frames), []);
});
