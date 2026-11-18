#!/usr/bin/env node
// Scaffold a playable game project from assets/starter: vendor three.js locally (no CDN at
// runtime), copy the MandarinAi logo, and prepare the requested cast models.
//
// Usage (from the skill root, after `npm install`):
//   node scripts/new-game.mjs --out /abs/output/games/<slug> --cast rat,ox
//   node scripts/new-game.mjs --out ... --cast none          (stand-ins only, no cast models)
// Then: node /abs/output/games/<slug>/serve.mjs  ->  http://localhost:5173/?auto
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const SKILL = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const out = opt('--out');
const cast = opt('--cast', 'rat,ox');
const fail = (m) => { console.error(`new-game: ${m}`); process.exit(1); };

if (!out || !path.isAbsolute(out)) fail('--out must be an absolute path to a new directory outside the skill');
if (path.resolve(out).startsWith(SKILL + path.sep)) fail('--out must be outside the skill directory');
if (fs.existsSync(out) && fs.readdirSync(out).length) fail(`${out} exists and is not empty; pick a new directory`);
const three = path.join(SKILL, 'node_modules/three');
if (!fs.existsSync(three)) fail(`three.js not installed: run \`npm install\` in ${SKILL}`);

fs.cpSync(path.join(SKILL, 'assets/starter'), out, { recursive: true });

// three.js: the core build plus only the addons the starter imports (GLTFLoader and its two helpers)
const vend = path.join(out, 'vendor/three');
for (const f of ['build/three.module.js', 'build/three.core.js', 'examples/jsm/loaders/GLTFLoader.js', 'examples/jsm/utils/BufferGeometryUtils.js', 'examples/jsm/utils/SkeletonUtils.js']) {
  const dst = path.join(vend, f.replace('examples/jsm/', 'jsm/'));
  fs.mkdirSync(path.dirname(dst), { recursive: true }); fs.copyFileSync(path.join(three, f), dst);
}
fs.copyFileSync(path.join(three, 'LICENSE'), path.join(vend, 'LICENSE'));

// brand: the real logo files, never a redrawn one
const brand = path.join(SKILL, '../mandarinai-illustration/assets/brand');
fs.mkdirSync(path.join(out, 'assets/brand'), { recursive: true });
for (const f of ['mandarinai-logo.png', 'mandarinai-icon.png']) fs.copyFileSync(path.join(brand, f), path.join(out, 'assets/brand', f));

if (cast !== 'none') {
  execFileSync(process.execPath, [path.join(SKILL, 'scripts/prepare-cast.mjs'), '--out', path.join(out, 'assets/cast'), ...cast.split(',').map((s) => s.trim()).filter(Boolean)], { stdio: 'inherit' });
} else {
  fs.mkdirSync(path.join(out, 'assets/cast'), { recursive: true });
  fs.writeFileSync(path.join(out, 'assets/cast/cast.json'), '{}\n');
}
console.log(`\nready: ${out}\n  node ${path.join(out, 'serve.mjs')}   then open http://localhost:5173/?auto`);
