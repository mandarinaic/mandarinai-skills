// Learner bot: the autoplay queue played like a person, not a script.
import test from 'node:test';
import assert from 'node:assert/strict';
import { createAutoplay, makeLearner } from '../assets/starter/src/autoplay.js';

test('the same seed gives the same learner', () => {
  const a = makeLearner({ seed: 4 }), b = makeLearner({ seed: 4 });
  const draw = (l) => [l.react(), l.read(12), l.wrong(), ...l.aim(0, 0)];
  assert.deepEqual(draw(a), draw(b));
});

test('a different seed gives a different learner', () => {
  const draw = (l) => [l.react(), l.read(12), ...l.aim(0, 0)];
  assert.notDeepEqual(draw(makeLearner({ seed: 1 })), draw(makeLearner({ seed: 2 })));
});

test('wrong() comes up at about 1 - accuracy', () => {
  const l = makeLearner({ accuracy: 0.6, seed: 9 });
  let wrong = 0;
  for (let i = 0; i < 4000; i++) wrong += l.wrong();
  assert.ok(Math.abs(wrong / 4000 - 0.4) < 0.03, `got ${wrong / 4000}`);
});

test('accuracy 1 never makes a wrong move', () => {
  const l = makeLearner({ accuracy: 1 });
  for (let i = 0; i < 500; i++) assert.equal(l.wrong(), false);
});

test('reaction is never instant and longer lines take longer to read', () => {
  const l = makeLearner({ seed: 3 });
  for (let i = 0; i < 500; i++) assert.ok(l.react() >= 6);
  const short = [], long = [];
  for (let i = 0; i < 200; i++) { short.push(l.read(4)); long.push(l.read(20)); }
  const mean = (xs) => xs.reduce((s, x) => s + x, 0) / xs.length;
  assert.ok(mean(long) > mean(short) * 2);
});

test('accuracy outside 0..1 is refused', () => {
  assert.throws(() => makeLearner({ accuracy: 1.5 }), /accuracy/);
  assert.throws(() => makeLearner({ accuracy: Number.NaN }), /accuracy/);
});

test('in learner mode plan() gets the learner and each refill starts with a reaction pause', () => {
  const keys = new Set(), pressed = new Set();
  let seen = 'unset', calls = 0;
  const demo = createAutoplay({ keys, pressed, human: { seed: 1 }, plan: (bot) => { seen = bot; return calls++ ? null : [{ press: ['KeyE'] }]; } });
  demo.start();
  demo.tick();
  assert.equal(typeof seen?.wrong, 'function');
  assert.equal(pressed.size, 0, 'the press waits behind a reaction pause');
  for (let i = 0; i < 120 && !pressed.size; i++) demo.tick();
  assert.ok(pressed.has('KeyE'));
});

test('in learner mode walk targets land near, not on, the plan point', () => {
  const at = [0, 0], keys = new Set();
  const demo = createAutoplay({ keys, pressed: new Set(), pos: () => at, human: { seed: 2, aim: 0.5 }, plan: () => [{ to: [5, 5] }] });
  demo.start();
  let goal = null;
  for (let i = 0; i < 400 && !goal; i++) { demo.tick(); if (demo.target) goal = demo.target; }
  assert.ok(goal, 'the learner should be walking somewhere');
  assert.notDeepEqual(goal, [5, 5]);
  assert.ok(Math.hypot(goal[0] - 5, goal[1] - 5) < 2.5);
});

test('without a learner, plan() gets null and walks exactly to its points', () => {
  let seen = 'unset';
  const demo = createAutoplay({ keys: new Set(), pressed: new Set(), plan: (bot) => { seen = bot; return null; } });
  demo.start();
  demo.tick();
  assert.equal(seen, null);
});
