// Autoplay: the game plays itself from a queue of scripted input steps, written into the
// same key sets the real keyboard fills. Uses: a ?demo run to watch or record a trailer,
// and scripted checks. Real input takes over (main.js calls stop()). Adapted from the
// OpenPixel "demo hand" queue (MIT, 喵老弟 / MarkMFFF). No DOM access, so tests run in node.
//
// Steps (one tick = one fixed logic step):
//   { hold: ['KeyW'], frames: 30 }   hold keys for N steps
//   { press: ['KeyE'] }              a one-step press
//   { wait: 90 }                     do nothing for N steps
//   { to: [x, z], within: 0.3 }      hold WASD toward a ground point (-z is W) until within
//                                    the radius, or `frames` (default 600) run out
// Any step may add  until: () => bool  (end early) and  then: () => {}  (run when it ends).
// plan() is called whenever the queue is empty; it returns more steps, or nothing to finish.
export function createAutoplay({ keys, pressed, pos = () => [0, 0], plan = null }) {
  let queue = [], k = 0, running = false;
  const mine = new Set();
  const hold = (code) => { mine.add(code); keys.add(code); };
  const release = () => { for (const c of mine) keys.delete(c); mine.clear(); };
  const finish = () => { const s = queue.shift(); k = 0; s.then?.(); };

  function walk(s) {
    const [x, z] = pos(), dx = s.to[0] - x, dz = s.to[1] - z, within = s.within ?? 0.3;
    if (Math.hypot(dx, dz) < within) return false;
    if (dx < -within / 2) hold('KeyA'); if (dx > within / 2) hold('KeyD');
    if (dz < -within / 2) hold('KeyW'); if (dz > within / 2) hold('KeyS');
    return true;
  }

  // Applies one step's input for this tick; false means the step ended without input.
  function apply(s) {
    if (s.until?.()) return false;
    k++;
    if (s.to && !walk(s)) return false;
    for (const c of s.hold || []) hold(c);
    if (k === 1) for (const c of s.press || []) pressed.add(c);
    if (k >= (s.frames ?? s.wait ?? (s.to ? 600 : 1))) finish();
    return true;
  }

  function tick() {
    if (!running) return false;
    release();
    for (let guard = 0; guard < 100; guard++) {
      if (!queue.length) {
        const more = plan?.();
        if (!more?.length) { running = false; return false; }
        queue.push(...more);
      }
      if (apply(queue[0])) return true;
      finish();
    }
    throw new Error('autoplay: 100 steps ended without input in one tick; plan() is looping');
  }

  return {
    get running() { return running; },
    start(steps = []) { queue = [...steps]; k = 0; running = true; },
    stop() { release(); queue = []; running = false; },
    tick,
  };
}
