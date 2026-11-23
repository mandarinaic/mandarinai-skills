// MandarinAi game starter: one scene, a playable cast member, an NPC, a scripted
// cutscene, collectible words, and the debug hooks every later stage relies on.
// URL switches: ?auto (skip title)  ?demo (plays itself; any key or tap takes over)  ?mute
//               ?show=cast (character lineup)  ?god (no gate lock)  ?paused (frames only via G.step)
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { keys, pressed, endFrame, debugPanel } from './input.js';
import { makeActor, animate, face, squash, flash, jump } from './motion.js';
import { createDialogue } from './dialogue.js';
import { story } from './story.js';
import { createFixedStep } from './loop.js';
import { createAutoplay } from './autoplay.js';

const Q = new URLSearchParams(location.search);
const G = (window.G = { errors: [], ready: false });
addEventListener('error', (e) => G.errors.push(String(e.message)));
addEventListener('unhandledrejection', (e) => G.errors.push(String(e.reason?.message || e.reason)));
const $ = (s) => document.querySelector(s);
const W = story.world;
// Reduced motion: the title camera holds still and toasts appear without the pop.
const calm = matchMedia('(prefers-reduced-motion: reduce)').matches;

// ---------- renderer, camera, light
const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
renderer.setSize(innerWidth, innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.05;
renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
$('#stage').appendChild(renderer.domElement);
renderer.domElement.addEventListener('webglcontextlost', (e) => { e.preventDefault(); G.errors.push('webgl context lost'); });

const scene = new THREE.Scene();
scene.background = new THREE.Color(0xdfe8f2);
scene.fog = new THREE.Fog(0xdfe8f2, 26, 60);
const camera = new THREE.PerspectiveCamera(innerWidth < innerHeight ? 50 : 38, innerWidth / innerHeight, 0.1, 200);
const CAM_OFFSET = new THREE.Vector3(0, 6.4, 7.8);   // ~40° down, close enough that a 1.1 m mascot reads
addEventListener('resize', () => {
  renderer.setSize(innerWidth, innerHeight); camera.aspect = innerWidth / innerHeight;
  camera.fov = innerWidth < innerHeight ? 50 : 38; camera.updateProjectionMatrix();
});

scene.add(new THREE.HemisphereLight(0xf4f1e8, 0x5d7a4a, 1.1));
const sun = new THREE.DirectionalLight(0xfff1d6, 2.2);
sun.position.set(-8, 16, 10); sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048); sun.shadow.bias = -0.0004; sun.shadow.normalBias = 0.02;
Object.assign(sun.shadow.camera, { left: -16, right: 16, top: 16, bottom: -16, near: 1, far: 50 });
scene.add(sun, sun.target);

// ---------- world (placeholder primitives: replace with generated props, see references/assets.md)
const rnd = mulberry32(7);
function mulberry32(a) { return () => { a |= 0; a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
const world = new THREE.Group(); scene.add(world);
{
  const g = new THREE.PlaneGeometry(70, 70, 70, 70); g.rotateX(-Math.PI / 2);
  const col = [], c = new THREE.Color();
  for (let i = 0; i < g.attributes.position.count; i++) { c.setHSL(0.22 + rnd() * 0.04, 0.32, 0.44 + rnd() * 0.05); col.push(c.r, c.g, c.b); }
  g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
  const ground = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.95 }));
  ground.receiveShadow = true; ground.name = 'ground'; world.add(ground);

  const water = new THREE.Mesh(new THREE.PlaneGeometry(70, W.river[1] - W.river[0]).rotateX(-Math.PI / 2),
    new THREE.MeshStandardMaterial({ color: 0x3b78b8, roughness: 0.15, metalness: 0.1, transparent: true, opacity: 0.92 }));
  water.position.set(0, 0.02, (W.river[0] + W.river[1]) / 2); water.receiveShadow = true; world.add(water); G.water = water;

  // grass: thin bent blades, instanced, colour-varied; never one mesh per plant
  const blade = new THREE.PlaneGeometry(0.05, 0.34, 1, 3); blade.translate(0, 0.17, 0);
  const bp = blade.attributes.position; for (let i = 0; i < bp.count; i++) { const y = bp.getY(i) / 0.34; bp.setX(i, bp.getX(i) * (1 - y)); bp.setZ(i, y * y * 0.08); }
  blade.computeVertexNormals();
  const grass = new THREE.InstancedMesh(blade, new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 1, side: THREE.DoubleSide }), 14000);
  const m = new THREE.Matrix4(), q = new THREE.Quaternion(), s = new THREE.Vector3(), p = new THREE.Vector3(), e = new THREE.Euler();
  for (let i = 0; i < grass.count; i++) {
    let x, z; do { x = (rnd() - 0.5) * 36; z = (rnd() - 0.5) * 48; } while (z > W.river[0] - 0.3 && z < W.river[1] + 0.3);
    q.setFromEuler(e.set((rnd() - 0.5) * 0.3, rnd() * 6.3, (rnd() - 0.5) * 0.3)); s.set(1, 0.6 + rnd() * 0.9, 1);
    grass.setMatrixAt(i, m.compose(p.set(x, 0, z), q, s)); grass.setColorAt(i, c.setHSL(0.2 + rnd() * 0.06, 0.45, 0.32 + rnd() * 0.12));
  }
  grass.receiveShadow = true; world.add(grass);

  const stone = new THREE.MeshStandardMaterial({ color: 0x8b8a83, roughness: 0.9, flatShading: true });
  for (let i = 0; i < 26; i++) {
    const r = new THREE.Mesh(new THREE.DodecahedronGeometry(0.3 + rnd() * 0.6, 0), stone);
    r.position.set((rnd() < 0.5 ? -1 : 1) * (8 + rnd() * 6), 0.1, (rnd() - 0.5) * 40); r.scale.y = 0.6;
    r.rotation.set(rnd(), rnd() * 6, rnd()); r.castShadow = r.receiveShadow = true; world.add(r);
  }

  // 牌坊 (memorial archway), not a torii: beams sit BETWEEN the pillars, a plaque
  // hangs between them, and a hipped tile roof with flared eaves caps the top.
  const gate = new THREE.Group(); gate.position.set(W.gate[0], 0, W.gate[1]); gate.name = 'gate';
  const lacquer = new THREE.MeshStandardMaterial({ color: 0x1b46a2, roughness: 0.55 });
  const gold = new THREE.MeshStandardMaterial({ color: 0xffc107, roughness: 0.35, metalness: 0.4 });
  const tile = new THREE.MeshStandardMaterial({ color: 0x2e3442, roughness: 0.75 });
  const stoneBase = new THREE.MeshStandardMaterial({ color: 0xc9c3b4, roughness: 0.9 });
  const span = 4.2, top = 3.7;
  for (const x of [-span / 2, span / 2]) {
    const pl = new THREE.Mesh(new THREE.BoxGeometry(0.36, top, 0.36), lacquer); pl.position.set(x, top / 2, 0); gate.add(pl);
    const base = new THREE.Mesh(new THREE.BoxGeometry(0.7, 0.5, 0.9), stoneBase); base.position.set(x, 0.25, 0); gate.add(base);
  }
  for (const [y, h] of [[2.75, 0.28], [3.45, 0.32]]) { const b = new THREE.Mesh(new THREE.BoxGeometry(span - 0.36, h, 0.3), lacquer); b.position.y = y; gate.add(b); }
  const plaqueTex = (() => { const cv = document.createElement('canvas'); cv.width = 512; cv.height = 192; const x = cv.getContext('2d');
    x.fillStyle = '#1b46a2'; x.fillRect(0, 0, 512, 192); x.strokeStyle = '#ffc107'; x.lineWidth = 12; x.strokeRect(10, 10, 492, 172);
    x.fillStyle = '#ffc107'; x.font = '700 120px "Songti SC","Noto Serif SC","STSong",serif'; x.textAlign = 'center'; x.textBaseline = 'middle';
    x.fillText(story.gateText || '天门', 256, 100); const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace; return t; })();
  const plaque = new THREE.Mesh(new THREE.BoxGeometry(1.5, 0.56, 0.08), [gold, gold, gold, gold, new THREE.MeshStandardMaterial({ map: plaqueTex, roughness: 0.5 }), gold]);
  plaque.position.set(0, 3.1, 0.17); gate.add(plaque);
  // hipped roof: a frustum (4-sided cylinder) whose eaves corners are pulled up
  const roofG = new THREE.CylinderGeometry(0.55, 1.0, 0.7, 4, 1, false, Math.PI / 4); roofG.scale(span * 0.95, 1, 1.5);
  const rp = roofG.attributes.position; for (let i = 0; i < rp.count; i++) if (rp.getY(i) < 0) rp.setY(i, rp.getY(i) + 0.22 * Math.min(1, Math.abs(rp.getX(i)) / (span * 0.95 * 0.7)));
  roofG.computeVertexNormals();
  const roof = new THREE.Mesh(roofG, tile); roof.position.y = top + 0.32; gate.add(roof);
  const ridge = new THREE.Mesh(new THREE.BoxGeometry(span * 1.05, 0.14, 0.18), tile); ridge.position.y = top + 0.72; gate.add(ridge);
  for (const x of [-1, 1]) { const orn = new THREE.Mesh(new THREE.ConeGeometry(0.11, 0.38, 8), gold); orn.position.set(x * span * 0.53, top + 0.86, 0); orn.rotation.z = -x * 0.35; gate.add(orn); }
  gate.traverse((o) => { if (o.isMesh) o.castShadow = o.receiveShadow = true; });
  world.add(gate);
}

// ---------- cast
// single-file builds (build-single-html.mjs) inline assets: route three's loaders through that table
if (window.__assetURL) THREE.DefaultLoadingManager.setURLModifier(window.__assetURL);
const loader = new GLTFLoader();
async function loadCast() {
  const res = await fetch('assets/cast/cast.json');
  if (!res.ok) throw new Error('assets/cast/cast.json missing: run scripts/prepare-cast.mjs into this game');
  const manifest = await res.json();
  const ids = Q.get('show') === 'cast' ? Object.keys(manifest) : [...new Set(Object.values(story.cast).filter(Boolean))];
  const out = {};
  await Promise.all(ids.map(async (id) => {
    if (!manifest[id]) throw new Error(`cast "${id}" not prepared: run prepare-cast.mjs ${id}`);
    const gltf = await loader.loadAsync(`assets/cast/${manifest[id].file}`);
    out[id] = { scene: gltf.scene, meta: manifest[id] };
  }));
  return out;
}
const standIn = () => new THREE.Mesh(new THREE.CapsuleGeometry(0.3, 0.5, 4, 12).translate(0, 0.55, 0), new THREE.MeshStandardMaterial({ color: 0x9aa3b5 }));
const actorFor = (cast, role, opts) => { const id = story.cast[role]; return makeActor(id ? cast[id].scene.clone(true) : standIn(), opts); };

// ---------- HUD, audio
const dialogue = createDialogue({ el: $('#dialogue'), names: story.names, errors: G.errors });
let audio = null; const muted = Q.has('mute') || Q.has('auto');
function blip(freq, dur = 0.18, type = 'sine', gain = 0.12) {   // placeholder cue; swap for CC0 samples (references/vfx-ui-audio.md)
  if (muted) return; audio ||= new AudioContext();
  const o = audio.createOscillator(), g = audio.createGain(), t = audio.currentTime;
  o.type = type; o.frequency.value = freq; g.gain.setValueAtTime(gain, t); g.gain.exponentialRampToValueAtTime(0.001, t + dur);
  o.connect(g).connect(audio.destination); o.start(t); o.stop(t + dur);
}
const toasts = [];   // aged in game time, not setTimeout, so frame-stepped tests see them expire
function toast(html) { const t = document.createElement('div'); t.className = 'toast'; t.innerHTML = html; $('#toasts').appendChild(t); toasts.push({ el: t, age: 0 }); }
function ageToasts(dt) { for (let i = toasts.length - 1; i >= 0; i--) if ((toasts[i].age += dt) > 2.2) { toasts[i].el.remove(); toasts.splice(i, 1); } }
const objective = (zh, en) => { $('#objective').innerHTML = `<b>${zh}</b><span>${en}</span>`; };

// ---------- game state
let mode = 'loading', player, ferry, crossed = false, cut = null, gateNag = false;
let clock = 0;   // game seconds; animate from this, never performance.now(), so stepped runs repeat exactly
const collected = [], wordMeshes = [], tmp = new THREE.Vector3();
const focus = new THREE.Vector3(), tapTarget = { on: false, x: 0, z: 0 };
const dist2 = (a, x, z) => Math.hypot(a.root.position.x - x, a.root.position.z - z);

function wordSprite(w) {
  const c = document.createElement('canvas'); c.width = c.height = 256; const g = c.getContext('2d');
  g.fillStyle = '#ffc107'; g.beginPath(); g.arc(128, 128, 118, 0, 7); g.fill();
  g.lineWidth = 10; g.strokeStyle = '#1b46a2'; g.stroke();
  g.fillStyle = '#1b46a2'; g.font = '700 150px "PingFang SC","Noto Sans SC","Microsoft YaHei",sans-serif';
  g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(w.zh, 128, 138);
  const tex = new THREE.CanvasTexture(c); tex.colorSpace = THREE.SRGBColorSpace;
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex })); sp.scale.setScalar(0.9);
  sp.position.set(w.at[0], 1, w.at[1]); sp.userData.word = w; return sp;
}

function setupPlay(cast) {
  player = actorFor(cast, 'player'); player.root.position.set(W.start[0], 0, W.start[1]); player.root.rotation.y = Math.PI;
  ferry = actorFor(cast, 'ferry', { hopHeight: 0.04 }); ferry.root.position.set(W.ferry[0], 0, W.ferry[1]); ferry.root.rotation.y = -Math.PI / 2;
  ferry.root.scale.setScalar(story.scale?.ferry ?? 1);   // per-role scale lives in story.js, not in the model
  scene.add(player.root, ferry.root);
  for (const w of story.words) { const s = wordSprite(w); wordMeshes.push(s); scene.add(s); }
  focus.copy(player.root.position);
  objective('找老牛过河', 'Find Bo the ox to cross the river');
  G.player = player; G.ferry = ferry;
}

function setupLineup(cast) {
  world.visible = false; scene.fog = null; scene.background = new THREE.Color(0xfbf8f1);
  const floor = new THREE.Mesh(new THREE.CircleGeometry(30, 48).rotateX(-Math.PI / 2), new THREE.MeshStandardMaterial({ color: 0xf1ece0, roughness: 1 }));
  floor.receiveShadow = true; scene.add(floor);
  const ids = Object.keys(cast), perRow = Math.min(ids.length, 7), gap = 1.6, rows = Math.ceil(ids.length / perRow);
  ids.forEach((id, i) => {
    const a = makeActor(cast[id].scene); a.root.position.set((i % perRow - (perRow - 1) / 2) * gap, 0, -Math.floor(i / perRow) * 3.2); scene.add(a.root);
    const c = document.createElement('div'); c.className = 'tag'; c.textContent = `${cast[id].meta.name} · ${id} · ${cast[id].meta.height} m`; $('#tags').appendChild(c);
    a.tag = c; (G.lineup ||= []).push(a);
  });
  // fit the widest row in the view
  const halfW = (perRow * gap) / 2 + 0.4, fov = THREE.MathUtils.degToRad(camera.fov), d = halfW / Math.tan(fov / 2) / camera.aspect;
  camera.position.set(0, 1.4 + rows * 1.1, Math.max(4, d) * 0.85); camera.lookAt(0, 0.7, -(rows - 1) * 1.6);
  sun.position.set(-4, 10, 8); sun.target.position.set(0, 0, -(rows - 1) * 1.2);
  $('#title').hidden = true; mode = 'lineup';
}
G.spin = (on = true) => { G.lineupSpin = on; };

// ---------- per-frame logic
// Dialogue completion is a plain callback, never a Promise: microtasks do not run between
// G.step() frames, so a promise-based flow would stall every scripted test.
function talk(lines, next) { mode = 'talk'; player.speed = 0; dialogue.play(lines, () => { pressed.clear(); next ? next() : (mode = 'play'); }); }

function updatePlayer(dt) {
  let ix = 0, iz = 0;
  if (keys.has('KeyA') || keys.has('ArrowLeft')) ix -= 1; if (keys.has('KeyD') || keys.has('ArrowRight')) ix += 1;
  if (keys.has('KeyW') || keys.has('ArrowUp')) iz -= 1; if (keys.has('KeyS') || keys.has('ArrowDown')) iz += 1;
  if (ix || iz) tapTarget.on = false;
  else if (tapTarget.on) { ix = tapTarget.x - player.root.position.x; iz = tapTarget.z - player.root.position.z; if (Math.hypot(ix, iz) < 0.2) tapTarget.on = false; }
  const len = Math.hypot(ix, iz) || 1; ix /= len; iz /= len;
  const want = (ix || iz) ? player.maxSpeed : 0;
  player.speed += (want - player.speed) * Math.min(1, dt * 10);
  const p = player.root.position; const nx = p.x + ix * player.speed * dt; let nz = p.z + iz * player.speed * dt;
  // the river is a wall until the ferry has carried you; never accept an illegal position
  if (!crossed && nz < W.river[1] + 0.35) nz = Math.max(nz, W.river[1] + 0.35);
  if (crossed && nz > W.river[0] - 0.35) nz = Math.min(nz, W.river[0] - 0.35);
  p.x = THREE.MathUtils.clamp(nx, -W.halfWidth, W.halfWidth); p.z = THREE.MathUtils.clamp(nz, W.far, W.near);
  face(player, ix, iz, dt);
  // keep bodies apart
  const d = dist2(player, ferry.root.position.x, ferry.root.position.z);
  const r = 0.55 + 0.55 * (story.scale?.ferry ?? 1);
  if (d < r && d > 1e-3) { tmp.subVectors(p, ferry.root.position).setY(0).setLength(r); p.x = ferry.root.position.x + tmp.x; p.z = ferry.root.position.z + tmp.z; }
}

function updateWorld(dt) {
  for (const s of wordMeshes) if (s.visible) s.position.y = 1 + Math.sin(clock * 2 + s.position.x) * 0.12;
  const act = pressed.has('Space') || pressed.has('KeyE') || pressed.has('Tap');
  if (!crossed && dist2(player, ferry.root.position.x, ferry.root.position.z) < 2.2) {
    face(ferry, player.root.position.x - ferry.root.position.x, player.root.position.z - ferry.root.position.z, dt, 4);
    $('#prompt').hidden = false;
    if (act) { $('#prompt').hidden = true; talk(story.lines.ferry, startFerry); return; }
  } else $('#prompt').hidden = true;
  for (const s of wordMeshes) {
    if (!s.visible || dist2(player, s.position.x, s.position.z) > 0.9) continue;
    s.visible = false; collected.push(s.userData.word); squash(player, 0.7); flash(player, 0.6); blip(880 + collected.length * 220, 0.35, 'triangle');
    const w = s.userData.word; toast(`<b>${w.zh}</b><i>${w.py}</i><span>${w.en}</span>`);
    $('#bag').innerHTML = collected.map((x) => `<b title="${x.py} · ${x.en}">${x.zh}</b>`).join('');
    if (collected.length === story.words.length) objective('去大门', 'Run to the gate');
    else objective(`收集三个字 ${collected.length}/${story.words.length}`, 'Collect three characters, then reach the gate');
  }
  const atGate = dist2(player, W.gate[0], W.gate[1] + 1) < 2;
  if (atGate && collected.length === story.words.length || atGate && Q.has('god')) { finish(); return; }
  if (atGate && !gateNag) { gateNag = true; talk(story.lines.gateLocked); }
  if (!atGate) gateNag = false;
}

function startFerry() {
  mode = 'cut'; jump(player, 3.6);
  const from = ferry.root.position.clone(), to = new THREE.Vector3(W.farBank[0] + 1.2, 0, W.farBank[1]);
  cut = { t: 0, dur: 4.2, from, to };
}
function updateCut(dt) {
  cut.t += dt; const k = Math.min(cut.t / cut.dur, 1), e = k < 0.5 ? 2 * k * k : 1 - (-2 * k + 2) ** 2 / 2;
  const prev = ferry.root.position.clone(); ferry.root.position.lerpVectors(cut.from, cut.to, e);
  const v = ferry.root.position.clone().sub(prev); ferry.speed = v.length() / Math.max(dt, 1e-4); face(ferry, v.x, v.z, dt, 3);
  // ride on the back: the ox's height comes from the manifest, never from the mesh
  player.root.position.copy(ferry.root.position).add(new THREE.Vector3(0, (ferry.height || 1.1) * 0.62 , 0));
  player.root.rotation.y = ferry.root.rotation.y; player.speed = 0;
  if (k >= 1) {
    crossed = true; cut = null; ferry.speed = 0;
    player.root.position.set(W.farBank[0] - 0.6, 0, W.farBank[1] - 1); jump(player, 3); mode = 'play';
    objective(`收集三个字 0/${story.words.length}`, 'Collect three characters, then reach the gate');
  }
}

function finish() {
  mode = 'end'; player.speed = 0; blip(523, 0.4); blip(784, 0.6);
  talk(story.lines.finish, () => {
    mode = 'end';
    $('#end-words').innerHTML = collected.map((w) => `<li><b>${w.zh}</b><i>${w.py}</i><span>${w.en}</span></li>`).join('');
    $('#end').hidden = false; $('#hud').hidden = true; for (const t of toasts.splice(0)) t.el.remove();
  });
}

function updateCamera(dt) {
  if (mode === 'title') {
    const t = calm ? 0 : clock / 6; camera.position.set(Math.sin(t) * 16, 9, Math.cos(t) * 16 - 2); camera.lookAt(0, 0, -2); return;
  }
  // leash: the focus trails the player but never more than 3 m away
  const p = player.root.position; focus.lerp(p, 1 - Math.exp(-dt * 6));
  if (focus.distanceTo(p) > 3) focus.copy(p).add(tmp.subVectors(focus, p).setLength(3));
  camera.position.copy(focus).add(CAM_OFFSET);   // one smoothing stage only: a second lerp drags the player off-centre
  camera.lookAt(focus.x, focus.y + 0.5, focus.z);
  sun.position.set(focus.x - 8, 16, focus.z + 10); sun.target.position.copy(focus);
}

function frame(dt, draw = true) {
  clock += dt;
  if (demo.running) demo.tick();
  if (mode === 'lineup') {
    for (const a of G.lineup) { if (G.lineupSpin) a.root.rotation.y += dt * 0.6; animate(a, dt);
      tmp.copy(a.root.position).setY(-0.15).project(camera); a.tag.style.transform = `translate(${(tmp.x + 1) * innerWidth / 2}px,${(1 - tmp.y) * innerHeight / 2}px) translate(-50%,0)`; }
  } else if (player) {
    if (mode === 'play') { updatePlayer(dt); updateWorld(dt); } else if (mode === 'cut') updateCut(dt);
    if (mode === 'talk') { pressed.clear(); }
    animate(player, dt); animate(ferry, dt);
    if (G.water) G.water.material.color.setHSL(0.58, 0.5, 0.47 + Math.sin(clock / 0.7) * 0.015);
    ageToasts(dt);
    updateCamera(dt);
  }
  if (draw) { renderer.render(scene, camera); panel(); }
  endFrame();
}

// ---------- autoplay (?demo): the starter plays its own story. Replace demoPlan with the
// adapted story's route; keep it reading only game state so it stays repeatable.
const READ = 150;   // steps a line stays up in the demo (2.5 s) so a viewer can read it
const notPlaying = () => mode !== 'play';
function demoPlan() {
  if (mode === 'title') return [{ wait: 60, then: start }];
  if (mode === 'talk') return [{ wait: READ, until: () => !dialogue.open, then: () => dialogue.open && dialogue.advance() }];
  if (mode === 'cut') return [{ wait: 30 }];
  if (mode !== 'play') return null;   // end screen: the run is over
  if (!crossed) return [{ to: [ferry.root.position.x, ferry.root.position.z + 1.7], until: notPlaying }, { press: ['KeyE'] }];
  const next = wordMeshes.find((s) => s.visible);
  return [{ to: next ? [next.position.x, next.position.z] : [W.gate[0], W.gate[1] + 1], until: notPlaying }];
}
const demo = createAutoplay({ keys, pressed, pos: () => [player.root.position.x, player.root.position.z], plan: demoPlan });
// a real key or tap ends the demo and hands the game over where it stands
for (const ev of ['keydown', 'pointerdown']) addEventListener(ev, (e) => { if (e.isTrusted && demo.running) demo.stop(); }, true);

// ---------- debug hooks (tabs in the background do not run rAF: drive frames by hand)
const panel = debugPanel(() => player ? `mode ${mode}  pos ${player.root.position.x.toFixed(2)},${player.root.position.z.toFixed(2)}  speed ${player.speed.toFixed(2)}\ncrossed ${crossed}  words ${collected.length}/${story.words.length}  errors ${G.errors.length}` : `mode ${mode}`);
Object.assign(G, {
  step: (n = 60, dt = 1 / 60) => { for (let i = 0; i < n; i++) frame(dt); return G.state(); },          // logic + render: slow, keep n small
  upd: (n = 60, dt = 1 / 60) => { for (let i = 0; i < n; i++) frame(dt, false); return G.state(); },  // logic only: use for long scripted runs
  render: () => { renderer.render(scene, camera); },
  paused: Q.has('paused'),   // true stops the real-time loop; G.step / G.upd still advance the game
  press: (...codes) => codes.forEach((c) => pressed.add(c)),
  hold: (code, on = true) => (on ? keys.add(code) : keys.delete(code)),
  teleport: (x, z) => { player.root.position.set(x, 0, z); focus.copy(player.root.position); },
  advance: () => dialogue.advance(),
  demo,   // G.demo.start() / .stop() / .running: the ?demo autoplay
  start: () => start(),
  state: () => ({ mode, crossed, words: collected.map((w) => w.zh), pos: player ? [+player.root.position.x.toFixed(2), +player.root.position.z.toFixed(2)] : null, dialogue: dialogue.open, demo: demo.running, errors: [...G.errors] }),
});

// tap / click on the ground to walk there; tap the ferry to talk
const ray = new THREE.Raycaster(), ndc = new THREE.Vector2();
renderer.domElement.addEventListener('pointerdown', (e) => {
  if (mode !== 'play') return;
  ndc.set(e.clientX / innerWidth * 2 - 1, -(e.clientY / innerHeight) * 2 + 1); ray.setFromCamera(ndc, camera);
  if (ray.intersectObject(ferry.root, true).length) { pressed.add('Tap'); return; }
  const hit = ray.intersectObject(scene.getObjectByName('ground'))[0];
  if (hit) Object.assign(tapTarget, { on: true, x: hit.point.x, z: hit.point.z });
});

function start() {
  if (mode !== 'title') return;
  $('#title').hidden = true; mode = 'talk'; $('#hud').hidden = false;
  talk(story.lines.intro);
}
addEventListener('keydown', (e) => { if ((e.code === 'Space' || e.code === 'Enter') && mode === 'title') { e.preventDefault(); e.stopImmediatePropagation(); start(); } }, true);
$('#start').addEventListener('click', start);

// Fixed 60 Hz logic, one render per display frame that advanced (src/loop.js).
const fixed = createFixedStep();
let last = performance.now();
function loop(now) {
  const n = G.paused ? 0 : fixed.advance((now - last) / 1000); last = now;   // G.paused: tests drive every frame
  for (let i = 0; i < n; i++) frame(fixed.dt, false);
  if (n) { renderer.render(scene, camera); panel(); }
  requestAnimationFrame(loop);
}

// ---------- boot
document.title = `${story.title.zh} · ${story.title.en} | MandarinAi`;
$('#title-zh').textContent = story.title.zh; $('#title-en').textContent = story.title.en;
loadCast().then((cast) => {
  if (Q.get('show') === 'cast') { setupLineup(cast); }
  else {
    setupPlay(cast); ferry.height = (cast[story.cast.ferry]?.meta.height ?? 1.1) * (story.scale?.ferry ?? 1);
    mode = 'title'; $('#start').hidden = false; $('#loading').hidden = true;
    if (Q.has('auto')) start();
    if (Q.has('demo')) demo.start();
  }
  G.ready = true; requestAnimationFrame(loop);
}).catch((e) => { G.errors.push(e.message); $('#loading').textContent = e.message; console.error(e); });
