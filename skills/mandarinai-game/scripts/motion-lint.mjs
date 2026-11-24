// Motion lint: finds glitches in per-step actor samples, the way a viewer would see them.
// Used by play-check --motion; the samples come from the game's G.motion() (motion.js sample()).
// Idea from goofyfish's check-motion (MIT, Kamran Ahmed), which checks 2D stick-figure limbs;
// here the logic is frame-stepped, so every sample is exactly 1/60 s apart and no frame is skipped.
//
// frames: [[{ id, x, y, z, ry, sx, sy, sz, placed }, ...], ...]   one array per logic step
//   x, y, z  where the body is drawn (feet), metres;  ry facing, radians;  sx, sy, sz body scale
//   placed   true on the step a deliberate teleport happened (motion.js place()): not a snap
//
//   snap          position changes velocity by more than SNAP m in one step (a teleport or a
//                 hard cut on screen; a jump takeoff at 3.6 m/s is 0.06)
//   spin          facing turns more than SPIN rad in one step (an instant about-face)
//   below-ground  feet under y = 0
//   squash        body scale outside SQUASH (a squash or stretch that reads as a broken model)
//   nan           a non-finite number: the actor vanishes or the frame breaks
export const LIMITS = { SNAP: 0.1, SPIN: 0.35, GROUND: -0.02, SQUASH: [0.7, 1.3] };
const MERGE = 9;   // findings of one kind on one actor closer than this many steps are one finding

const wrap = (a) => Math.atan2(Math.sin(a), Math.cos(a));

export function lintMotion(frames, limits = LIMITS) {
  const found = [];
  const add = (kind, id, i, peak) => {
    const last = found.findLast((f) => f.kind === kind && f.id === id);
    if (last && i - last.to <= MERGE) { last.to = i; last.peak = Math.max(last.peak, peak); return; }
    found.push({ kind, id, from: i, to: i, peak });
  };
  const byId = frames.map((fr) => new Map(fr.map((s) => [s.id, s])));
  byId.forEach((now, i) => {
    for (const [id, s] of now) {
      const nums = [s.x, s.y, s.z, s.ry, s.sx, s.sy, s.sz];
      if (nums.some((v) => !Number.isFinite(v))) { add('nan', id, i, 0); continue; }
      if (s.y < limits.GROUND) add('below-ground', id, i, -s.y);
      const sq = Math.max(...[s.sx, s.sy, s.sz].map((v) => Math.max(limits.SQUASH[0] - v, v - limits.SQUASH[1])));
      if (sq > 0) add('squash', id, i, sq);
      const prev = byId[i - 1]?.get(id), next = byId[i + 1]?.get(id);
      if (!prev || s.placed) continue;   // first step on screen, or a declared teleport
      const turn = Math.abs(wrap(s.ry - prev.ry));
      if (turn > limits.SPIN) add('spin', id, i, turn);
      if (!next || next.placed) continue;
      const accel = Math.hypot(next.x - 2 * s.x + prev.x, next.y - 2 * s.y + prev.y, next.z - 2 * s.z + prev.z);
      if (accel > limits.SNAP) add('snap', id, i, accel);
    }
  });
  return found.map((f) => ({ ...f, peak: +f.peak.toFixed(3) }));
}
