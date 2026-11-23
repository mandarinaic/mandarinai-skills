// Fixed-step clock: logic advances in whole 1/60 s steps whatever the display refresh rate.
import test from 'node:test';
import assert from 'node:assert/strict';
import { createFixedStep } from '../assets/starter/src/loop.js';

test('one 60 Hz display frame runs exactly one logic step', () => {
  const clock = createFixedStep();
  assert.equal(clock.advance(1 / 60), 1);
});

test('a 120 Hz display runs one logic step every second frame', () => {
  const clock = createFixedStep();
  assert.deepEqual([1, 2, 3, 4].map(() => clock.advance(1 / 120)), [0, 1, 0, 1]);
});

test('a long stall runs at most maxSteps and drops the backlog', () => {
  const clock = createFixedStep({ maxSteps: 5 });
  assert.equal(clock.advance(2), 5);
  assert.equal(clock.advance(1 / 60), 1);
});

test('a clock that goes backwards runs no steps', () => {
  assert.equal(createFixedStep().advance(-1), 0);
});

test('dt is the fixed step length', () => {
  assert.equal(createFixedStep({ hz: 30 }).dt, 1 / 30);
});
