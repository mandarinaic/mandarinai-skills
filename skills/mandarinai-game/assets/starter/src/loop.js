// Fixed-step game clock. Logic always advances in whole 1/hz steps, so a 144 Hz monitor,
// a 60 Hz laptop and a frame-stepped test all simulate the same game; rendering happens
// at most once per display frame. Pattern adapted from OpenPixel (MIT, 喵老弟 / MarkMFFF).
//
// Usage:
//   const clock = createFixedStep();
//   function loop(now) { const n = clock.advance((now - last) / 1000); last = now;
//     for (let i = 0; i < n; i++) update(clock.dt); if (n) render(); requestAnimationFrame(loop); }
export function createFixedStep({ hz = 60, maxSteps = 5 } = {}) {
  const dt = 1 / hz;
  let acc = 0;
  return {
    dt,
    // wall-clock seconds since the last call -> how many logic steps to run now
    advance(seconds) {
      acc += Math.max(0, seconds);
      let n = Math.floor(acc / dt + 1e-6);
      // A stall (tab switch, GC, slow GPU) drops the backlog: the game slows down for a
      // moment instead of running one huge step that tunnels through walls.
      if (n > maxSteps) { n = maxSteps; acc = 0; } else acc -= n * dt;
      return n;
    },
  };
}
