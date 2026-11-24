// Autoplay: the game plays itself from a queue of scripted input steps, written into the
// same key sets the real keyboard fills. Uses: a ?demo run to watch or record a trailer,
// a ?bot run that plays like a learner, and scripted checks. Real input takes over
// (main.js calls stop()). Adapted from the OpenPixel "demo hand" queue (MIT, 喵老弟 /
// MarkMFFF); the learner bot follows goofyfish's ?bot (MIT, Kamran Ahmed). No DOM access,
// so tests run in node.
//
// Steps (one tick = one fixed logic step):
//   { hold: ['KeyW'], frames: 30 }   hold keys for N steps
//   { press: ['KeyE'] }              a one-step press
//   { wait: 90 }                     do nothing for N steps
//   { to: [x, z], within: 0.3 }      hold WASD toward a ground point (-z is W) until within
//                                    the radius, or `frames` (default 600) run out
// Any step may add  until: () => bool  (end early) and  then: () => {}  (run when it ends).
// plan(bot) is called whenever the queue is empty; it returns more steps, or nothing to finish.
// bot is null for the perfect ?demo route, or the learner (makeLearner) when `human` is set:
// then every refill starts with a reaction pause and walk targets land a little off.

// Seeded so a learner run repeats exactly: same seed, same pauses, same mistakes.
function mulberry32(a) {
  return () => { a |= 0; a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}

// A learner at a given accuracy: decent, never perfect. Times are in logic steps (1/60 s).
//   accuracy  chance a decision is right; wrong() is true at 1 - accuracy
//   react     [mean, sd] pause before acting (default 0.3 s ± 0.1 s, never under 0.1 s)
//   aim       sd in metres of where a walk actually ends up aiming
//   cps       reading speed in characters per second
export function makeLearner({ accuracy = 0.7, seed = 1, react = [18, 6], aim = 0.35, cps = 4 } = {}) {
  if (!(accuracy >= 0 && accuracy <= 1)) throw new Error(`learner accuracy must be 0..1, got ${accuracy}`);
  const rng = mulberry32(seed);
  const gauss = () => Math.sqrt(-2 * Math.log(1 - rng())) * Math.cos(2 * Math.PI * rng());
  return {
    accuracy, seed, rng, gauss,
    wrong: () => rng() >= accuracy,
    react: () => Math.max(6, Math.round(react[0] + gauss() * react[1])),
    read: (chars) => Math.round(60 * (0.6 + chars / cps) * Math.max(0.6, 1 + gauss() * 0.2)),
    aim: (x, z) => [x + gauss() * aim, z + gauss() * aim],
  };
}

export function createAutoplay({ keys, pressed, pos = () => [0, 0], plan = null, human = null }) {
  let queue = [], k = 0, running = false, bot = null;
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

  // A person pauses before acting and walks roughly, not exactly, where they meant to.
  const humanize = (steps) => [{ wait: bot.react() }, ...steps.map((s) => (s.to ? { ...s, to: bot.aim(...s.to) } : s))];

  function tick() {
    if (!running) return false;
    release();
    for (let guard = 0; guard < 100; guard++) {
      if (!queue.length) {
        const more = plan?.(bot);
        if (!more?.length) { running = false; return false; }
        queue.push(...(bot ? humanize(more) : more));
      }
      if (apply(queue[0])) return true;
      finish();
    }
    throw new Error('autoplay: 100 steps ended without input in one tick; plan() is looping');
  }

  return {
    get running() { return running; },
    get learner() { return bot; },
    get target() { return queue[0]?.to ?? null; },   // where a walk step is heading now
    // Every start reseeds the learner, so a run depends only on its seed.
    start(steps = []) { bot = human ? makeLearner(human) : null; queue = [...steps]; k = 0; running = true; },
    stop() { release(); queue = []; running = false; },
    tick,
  };
}
