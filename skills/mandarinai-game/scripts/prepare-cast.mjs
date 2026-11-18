#!/usr/bin/env node
// Turn the MandarinAi character models (Tripo-style static meshes: ~180k triangles,
// Draco geometry, three 4096 PNG textures, Z-up node rotation) into game-ready GLBs:
// transform baked, Y-up, feet on y=0, centered, facing +Z, decimated, WebP textures,
// no decoder needed at runtime. Writes <out>/<name>.glb and <out>/cast.json.
//
// Usage (from the skill root):
//   node scripts/prepare-cast.mjs --out /abs/game/assets/cast jin xiang
//   node scripts/prepare-cast.mjs --out /abs/game/assets/cast --all
// Options: --src DIR (default $MANDARINAI_CAST_3D or ~/Downloads/3D/final)
//          --tris N (default 12000)  --tex N (default 1024)  --height M (override the roster's in-game height for every named character)
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS, KHRDracoMeshCompression, KHRMaterialsSpecular } from '@gltf-transform/extensions';
import { dedup, prune, weld, simplify, textureCompress, clearNodeTransform, transformMesh, getBounds } from '@gltf-transform/functions';
import { MeshoptSimplifier } from 'meshoptimizer';
import draco3d from 'draco3dgltf';
import sharp from 'sharp';

const SKILL = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const ROSTER = JSON.parse(fs.readFileSync(path.join(SKILL, 'assets/cast-roster.json'), 'utf8'));

function parseArgs(argv) {
  const o = { src: process.env.MANDARINAI_CAST_3D || path.join(os.homedir(), 'Downloads/3D/final'), tris: 12000, tex: 1024, names: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--out') o.out = argv[++i];
    else if (a === '--src') o.src = argv[++i];
    else if (a === '--tris') o.tris = Number(argv[++i]);
    else if (a === '--tex') o.tex = Number(argv[++i]);
    else if (a === '--height') o.height = Number(argv[++i]);
    else if (a === '--all') o.names = Object.keys(ROSTER.characters);
    else if (a.startsWith('--')) throw new Error(`unknown option ${a}`);
    else o.names.push(a.toLowerCase());
  }
  if (!o.out) throw new Error('--out DIR is required (a directory inside the game project, not the skill)');
  if (!o.names.length) throw new Error(`name at least one character or pass --all. Known: ${Object.keys(ROSTER.characters).join(' ')}`);
  for (const n of o.names) if (!ROSTER.characters[n]) throw new Error(`unknown character "${n}". Known: ${Object.keys(ROSTER.characters).join(' ')}`);
  return o;
}

function triangleCount(root) {
  let t = 0;
  for (const m of root.listMeshes()) for (const p of m.listPrimitives()) t += (p.getIndices()?.getCount() ?? p.getAttribute('POSITION').getCount()) / 3;
  return Math.round(t);
}

// Bake every node transform into its mesh, then translate/scale/yaw the geometry so the
// model stands on y=0, centered on x/z, facing +Z (three.js convention: a camera on +Z sees the face).
function normalize(doc, { yaw, height }) {
  const root = doc.getRoot();
  const scene = root.listScenes()[0];
  for (const n of root.listNodes()) clearNodeTransform(n);
  const b = getBounds(scene);
  const h = b.max[1] - b.min[1];
  const s = height ? height / h : 1;
  const cx = (b.min[0] + b.max[0]) / 2, cz = (b.min[2] + b.max[2]) / 2;
  const c = Math.cos(yaw), si = Math.sin(yaw);
  // column-major 4x4: scale, then yaw about Y, after moving the feet-center to the origin
  const m = [
    s * c, 0, -s * si, 0,
    0, s, 0, 0,
    s * si, 0, s * c, 0,
    0, 0, 0, 1,
  ];
  const tx = -cx, ty = -b.min[1], tz = -cz;
  m[12] = (m[0] * tx + m[4] * ty + m[8] * tz);
  m[13] = (m[1] * tx + m[5] * ty + m[9] * tz);
  m[14] = (m[2] * tx + m[6] * ty + m[10] * tz);
  for (const mesh of root.listMeshes()) transformMesh(mesh, m);
  const nb = getBounds(scene);
  return { height: +(nb.max[1] - nb.min[1]).toFixed(3), width: +(nb.max[0] - nb.min[0]).toFixed(3), depth: +(nb.max[2] - nb.min[2]).toFixed(3) };
}

async function main() {
  const o = parseArgs(process.argv.slice(2));
  if (!fs.existsSync(o.src)) throw new Error(`source dir not found: ${o.src}. Set --src or MANDARINAI_CAST_3D to the folder holding <name>.glb`);
  fs.mkdirSync(o.out, { recursive: true });
  await MeshoptSimplifier.ready;
  const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ 'draco3d.decoder': await draco3d.createDecoderModule() });
  const manifestPath = path.join(o.out, 'cast.json');
  const manifest = fs.existsSync(manifestPath) ? JSON.parse(fs.readFileSync(manifestPath, 'utf8')) : {};

  for (const name of o.names) {
    const meta = ROSTER.characters[name];
    const src = path.join(o.src, `${name}.glb`);
    if (!fs.existsSync(src)) throw new Error(`missing ${src}`);
    const doc = await io.read(src);
    const root = doc.getRoot();
    if (root.listSkins().length || root.listAnimations().length) console.warn(`${name}: source now has a skeleton/animations — this script keeps them, but re-check references/cast-3d.md`);
    const before = triangleCount(root);
    // Draco is decoded on read; drop the extension so the output needs no decoder.
    root.listExtensionsUsed().filter((e) => e.extensionName === KHRDracoMeshCompression.EXTENSION_NAME).forEach((e) => e.dispose());
    // The Tripo export sets specularColorFactor 2.0, which reads as wet plastic under game lighting.
    root.listExtensionsUsed().filter((e) => e.extensionName === KHRMaterialsSpecular.EXTENSION_NAME).forEach((e) => e.dispose());
    const dims = normalize(doc, { yaw: (ROSTER.yawDegrees ?? 0) * Math.PI / 180, height: o.height || meta.height });
    await doc.transform(weld(), dedup());
    const ratio = Math.min(1, o.tris / before);
    if (ratio < 0.98) await doc.transform(simplify({ simplifier: MeshoptSimplifier, ratio, error: 0.02 }));
    await doc.transform(
      prune(),
      textureCompress({ encoder: sharp, targetFormat: 'webp', resize: [o.tex, o.tex], quality: 82 }),
    );
    root.listMaterials().forEach((mat) => mat.setDoubleSided(false));
    const out = path.join(o.out, `${name}.glb`);
    await io.write(out, doc);
    const after = triangleCount(root);
    manifest[name] = { file: `${name}.glb`, name: meta.name, kind: meta.kind, ...dims, triangles: after, rigged: false };
    console.log(`${name.padEnd(8)} ${before} -> ${after} tris, h ${dims.height}m, ${(fs.statSync(out).size / 1024).toFixed(0)} KB`);
  }
  fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2) + '\n');
  console.log(`wrote ${manifestPath}`);
}

main().catch((e) => { console.error(`prepare-cast: ${e.message}`); process.exit(1); });
