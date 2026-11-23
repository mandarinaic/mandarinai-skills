// Autoplay queue: scripted input written into the same key sets the player's keyboard uses.
import test from 'node:test';
import assert from 'node:assert/strict';
import { createAutoplay } from '../assets/starter/src/autoplay.js';

const rig = (opts = {}) => {
  const keys = new Set(), pressed = new Set();
  return { keys, pressed, demo: createAutoplay({ keys, pressed, ...opts }) };
};
const run = (demo, n) => { for (let i = 0; i < n; i++) demo.tick(); };

test('hold keeps keys down for its frames, then releases them', () => {
  const { keys, demo } = rig();
  demo.start([{ hold: ['KeyW'], frames: 3 }]);
  run(demo, 3);
  assert.ok(keys.has('KeyW'));
  demo.tick();
  assert.equal(keys.has('KeyW'), false);
});

test('press adds a one-step press', () => {
  const { pressed, demo } = rig();
  demo.start([{ press: ['KeyE'] }]);
  demo.tick();
  assert.ok(pressed.has('KeyE'));
});

test('then runs once when its step finishes', () => {
  let calls = 0;
  const { demo } = rig();
  demo.start([{ wait: 2, then: () => calls++ }]);
  run(demo, 5);
  assert.equal(calls, 1);
});

test('to walks toward the target and ends inside the radius', () => {
  const at = [0, 0];
  const { keys, demo } = rig({ pos: () => at });
  demo.start([{ to: [3, -2] }]);
  demo.tick();
  assert.deepEqual([...keys].sort(), ['KeyD', 'KeyW']);
  at[0] = 3; at[1] = -2;
  demo.tick();
  demo.tick();
  assert.equal(keys.size, 0);
  assert.equal(demo.running, false);
});

test('until ends a step early', () => {
  let done = false;
  const { demo } = rig();
  demo.start([{ wait: 100, until: () => done }]);
  demo.tick();
  done = true;
  demo.tick();
  demo.tick();
  assert.equal(demo.running, false);
});

test('plan refills the queue and returning nothing ends the run', () => {
  let rounds = 0;
  const { demo } = rig({ plan: () => (rounds++ < 2 ? [{ wait: 1 }] : null) });
  demo.start();
  run(demo, 10);
  assert.equal(rounds, 3);
  assert.equal(demo.running, false);
});

test('stop releases only the keys autoplay was holding', () => {
  const { keys, demo } = rig();
  keys.add('Space');
  demo.start([{ hold: ['KeyA'], frames: 10 }]);
  demo.tick();
  demo.stop();
  assert.deepEqual([...keys], ['Space']);
  assert.equal(demo.running, false);
});
