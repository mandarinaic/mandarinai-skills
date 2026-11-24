// Procedural motion for the MandarinAi cast. The source models are static meshes with
// no skeleton, so all life comes from moving the whole body: hop-bob, roll, lean into
// speed, breathing, squash-and-stretch, and per-actor hit flash. If a character is later
// rigged (references/cast-3d.md), play its clips on `actor.model` and keep these layers
// for squash and flash only.
import * as THREE from 'three';

// No Math.random() here: the same frames must pose the cast the same way (tests, ?demo, posters).
// Breathing offsets are spread by creation order (golden-ratio steps) so idle actors stay out of sync.
let made = 0;

export function makeActor(model, { id = `actor${made}`, maxSpeed = 4.5, hopHeight = 0.07 } = {}) {
  const root = new THREE.Group();   // position + facing: game logic writes here
  const body = new THREE.Group();   // procedural offsets: only this file writes here
  root.add(body); body.add(model);
  const mats = [];
  model.traverse((o) => {
    if (!o.isMesh) return;
    o.castShadow = true; o.receiveShadow = false;
    o.material = o.material.clone();   // per-actor, so a flash on one does not light the others
    o.material.emissive = new THREE.Color(0xffffff); o.material.emissiveIntensity = 0;
    mats.push(o.material);
  });
  return { id, root, body, model, mats, maxSpeed, hopHeight, speed: 0, phase: 0, t: (made++ * 6.18034) % 10, squash: 0, flash: 0, hop: 0, hopV: 0, freeze: 0, gait: 0, placing: false, placed: false };
}

// Move an actor somewhere at once, on purpose (a scene cut, a respawn). The motion lint
// (play-check --motion) skips this step instead of reporting a snap. Moving root.position by
// hand across a gap is what the lint is there to catch: arc or ease there instead.
export function place(actor, x, y, z) { actor.root.position.set(x, y, z); actor.placing = true; }

// One motion-lint sample: where the body is drawn (feet), facing, body scale, and whether this
// step was a place(). Read after the step's animate(); G.motion() returns one per actor.
export function sample(a) {
  const p = a.root.position, b = a.body.position, k = a.root.scale.y;
  return { id: a.id, x: p.x + b.x * k, y: p.y + b.y * k, z: p.z + b.z * k, ry: a.root.rotation.y, sx: a.body.scale.x, sy: a.body.scale.y, sz: a.body.scale.z, placed: a.placed };
}

// Turn toward a world-space direction at a capped rate (radians per second).
export function face(actor, dx, dz, dt, rate = 12) {
  if (Math.abs(dx) + Math.abs(dz) < 1e-4) return;
  const want = Math.atan2(dx, dz); let d = want - actor.root.rotation.y;
  d = Math.atan2(Math.sin(d), Math.cos(d));
  actor.root.rotation.y += Math.sign(d) * Math.min(Math.abs(d), rate * dt);
}

export const squash = (actor, amount = 1) => { actor.squash = Math.max(actor.squash, amount); };
export const flash = (actor, amount = 1) => { actor.flash = Math.max(actor.flash, amount); };
export const jump = (actor, v = 3.2) => { if (actor.hop <= 0) { actor.hopV = v; squash(actor, 0.6); } };
export const hitstop = (actor, seconds) => { actor.freeze = Math.max(actor.freeze, seconds); };

export function animate(actor, dt) {
  actor.placed = actor.placing; actor.placing = false;   // a place() before this animate belongs to this step
  if (actor.freeze > 0) { actor.freeze -= dt; dt = 0; actor.body.position.x = Math.sin(actor.freeze * 400) * 0.015; }   // shake driven by the countdown
  else actor.body.position.x = 0;
  actor.t += dt;
  const k = Math.min(actor.speed / actor.maxSpeed, 1);
  // the gait layers follow speed with a short lag: when a dialogue or a wall stops the actor
  // dead, the hop settles over a few frames instead of popping to the ground in one
  const g = (actor.gait += (k - actor.gait) * Math.min(1, dt * 12));
  actor.phase += dt * (6 + 8 * k) * (k > 0.02 ? 1 : 0);
  // a chibi gait is a hop, not a stride: bounce on |sin|, sway on sin
  const bob = Math.abs(Math.sin(actor.phase)) * actor.hopHeight * g;
  if (actor.hopV || actor.hop > 0) { actor.hopV -= 9.8 * dt; actor.hop += actor.hopV * dt; if (actor.hop <= 0) { actor.hop = 0; actor.hopV = 0; squash(actor, 0.8); } }
  actor.body.position.y = bob + actor.hop;
  actor.body.rotation.z = Math.sin(actor.phase) * 0.07 * g;
  actor.body.rotation.x = 0.13 * g;                           // lean into the run (+X tilts the top toward +Z, the facing)
  const breathe = 1 + Math.sin(actor.t * 2.4) * 0.012 * (1 - g);
  const s = actor.squash; actor.squash = Math.max(0, s - dt * 5);
  const wobble = s * Math.cos((1 - s) * 9);                   // a damped overshoot reads as weight
  actor.body.scale.set(1 + wobble * 0.12, breathe - wobble * 0.16, 1 + wobble * 0.12);
  actor.flash = Math.max(0, actor.flash - dt * 4);
  for (const m of actor.mats) m.emissiveIntensity = actor.flash * 0.6;
}
