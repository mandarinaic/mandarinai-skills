#!/usr/bin/env node
// Pack a game project into ONE self-contained HTML (double-click to play, zero network
// requests) plus a static site (dist/site/) for hosting. Generalized from the build script
// in guizang-game-skill (AGPL-3.0); see references/packaging.md.
//
// Usage (from the skill root):
//   node scripts/build-single-html.mjs /abs/game [--name slug] [--tex 1024] [--music-kbps 96]
// Expects the starter layout: index.html, src/main.js, vendor/three/, assets/**.
//   1. shrink assets (GLB textures -> WebP at --tex, big images resized, music re-encoded)
//   2. bundle src/main.js with esbuild (three resolved to the vendored copy)
//   3. inline every asset as a data URL in window.__A; fetch() and three's loading
//      manager read from that table; anything under assets/ that is not packed returns 404
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { dedup, prune, textureCompress } from '@gltf-transform/functions';
import draco3d from 'draco3dgltf';
import sharp from 'sharp';
import { build } from 'esbuild';

const args = process.argv.slice(2);
const root = args[0] && path.resolve(args[0]);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const fail = (m) => { console.error(`build-single-html: ${m}`); process.exit(1); };
if (!root || !fs.existsSync(path.join(root, 'index.html'))) fail('usage: build-single-html.mjs /abs/game-dir  (must contain index.html)');
if (!fs.existsSync(path.join(root, 'src/main.js'))) fail(`${root}/src/main.js not found`);
const name = opt('--name', path.basename(root));
const TEX = Number(opt('--tex', 1024));
const KBPS = Number(opt('--music-kbps', 96));
const OUT = path.join(root, 'dist'), OPT = path.join(OUT, '.cache'), SITE = path.join(OUT, 'site');
fs.mkdirSync(OPT, { recursive: true }); fs.rmSync(SITE, { recursive: true, force: true });

const MIME = { '.glb': 'model/gltf-binary', '.gltf': 'model/gltf+json', '.json': 'application/json', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp', '.svg': 'image/svg+xml', '.mp3': 'audio/mpeg', '.ogg': 'audio/ogg', '.wav': 'audio/wav', '.m4a': 'audio/mp4', '.woff2': 'font/woff2', '.woff': 'font/woff', '.ttf': 'font/ttf', '.bin': 'application/octet-stream', '.ktx2': 'image/ktx2' };
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ 'draco3d.decoder': await draco3d.createDecoderModule() });
const hasFfmpeg = (() => { try { execFileSync('ffmpeg', ['-version'], { stdio: 'ignore' }); return true; } catch { return false; } })();
const A = {}; let rawBytes = 0, srcBytes = 0;
const mb = (n) => (n / 1e6).toFixed(2) + ' MB';

// re-shrink only when the source is newer than the cached result
async function cached(key, src, make) {
  const o = path.join(OPT, key.replace(/[\\/]/g, '__'));
  if (!fs.existsSync(o) || fs.statSync(o).mtimeMs < fs.statSync(src).mtimeMs) fs.writeFileSync(o, await make());
  return fs.readFileSync(o);
}
function put(key, buf) {
  const mime = MIME[path.extname(key).toLowerCase()];
  if (!mime) fail(`no MIME type for ${key}; add it to MIME or remove the file from assets/`);
  A[key] = `data:${mime};base64,${buf.toString('base64')}`; rawBytes += buf.length;
  const o = path.join(SITE, key); fs.mkdirSync(path.dirname(o), { recursive: true }); fs.writeFileSync(o, buf);
}
function walk(dir) { return fs.existsSync(dir) ? fs.readdirSync(dir, { withFileTypes: true }).flatMap((e) => (e.isDirectory() ? walk(path.join(dir, e.name)) : [path.join(dir, e.name)])) : []; }

// ---- 1. assets
for (const file of walk(path.join(root, 'assets'))) {
  const key = path.relative(root, file).split(path.sep).join('/');
  const ext = path.extname(file).toLowerCase();
  if (path.basename(file).startsWith('.') || /\/(SOURCES|README)\.md$/i.test(key) || ext === '.md' || ext === '.txt') continue;
  srcBytes += fs.statSync(file).size;
  let buf;
  if (ext === '.glb') {
    // No geometry quantization: it rescales meshes and breaks skinned characters (packaging.md).
    buf = await cached(`${key}.${TEX}`, file, async () => {
      const d = await io.read(file);
      await d.transform(dedup(), prune({ keepLeaves: true, keepAttributes: true }), textureCompress({ encoder: sharp, targetFormat: 'webp', resize: [TEX, TEX], quality: 82 }));
      return Buffer.from(await io.writeBinary(d));
    });
  } else if ((ext === '.png' || ext === '.jpg' || ext === '.jpeg') && fs.statSync(file).size > 600e3) {
    buf = await cached(`${key}.img`, file, async () => {
      const img = sharp(file).resize(2048, 2048, { fit: 'inside', withoutEnlargement: true });
      return ext === '.png' ? img.png({ palette: true, colours: 128 }).toBuffer() : img.jpeg({ quality: 82 }).toBuffer();
    });
  } else if (ext === '.mp3' && hasFfmpeg && /\/music\//.test(key)) {
    buf = await cached(`${key}.${KBPS}k`, file, async () => {
      const o = path.join(OPT, 'tmp.mp3'); execFileSync('ffmpeg', ['-y', '-v', 'error', '-i', file, '-ac', '2', '-b:a', `${KBPS}k`, o]);
      const b = fs.readFileSync(o); fs.unlinkSync(o); return b;
    });
  } else buf = fs.readFileSync(file);
  put(key, buf);
}
if (!hasFfmpeg) console.warn('ffmpeg not found: music copied as-is (no re-encode)');
console.log(`assets: ${Object.keys(A).length} files, ${mb(srcBytes)} -> ${mb(rawBytes)}`);

// ---- 2. code
const vend = path.join(root, 'vendor/three');
const r = await build({
  entryPoints: [path.join(root, 'src/main.js')], bundle: true, format: 'esm', minify: true, write: false, target: 'es2020', legalComments: 'none', charset: 'utf8',
  alias: { three: path.join(vend, 'build/three.module.js') },
  plugins: [{ name: 'addons', setup(b) { b.onResolve({ filter: /^three\/addons\// }, (a) => ({ path: path.join(vend, 'jsm', a.path.slice('three/addons/'.length)) })); } }],
});
const js = r.outputFiles[0].text;
console.log(`code: ${mb(js.length)}`);

// ---- 3. html
const src = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const MOD = /<script type="module" src="\.?\/?src\/main\.js"><\/script>/;
if (!MOD.test(src)) fail('index.html must load the game with <script type="module" src="./src/main.js"></script>');
const noMap = src.replace(/<script type="importmap">[\s\S]*?<\/script>\s*/, '');

// static site: same shrunk assets as files, code as one hashed module
const tag = `game.${crypto.createHash('md5').update(js).digest('hex').slice(0, 8)}.js`;
fs.writeFileSync(path.join(SITE, tag), js);
fs.writeFileSync(path.join(SITE, 'index.html'), noMap.replace(MOD, `<script type="module" src="${tag}"></script>`));
fs.writeFileSync(path.join(SITE, '.nojekyll'), '');

// single file: inline <img src>/url() references, then the lookup shim, then the module
let html = noMap.replace(/(["'(])((?:\.\/)?assets\/[^"')\s]+)/g, (m, q, u) => q + (A[u.replace(/^\.\//, '')] || u));
const shim = `window.__A=${JSON.stringify(A)};(()=>{const A=window.__A,k=u=>String(u).replace(location.href.replace(/[^/]*$/,''),'').replace(/^\\.\\//,'').split('?')[0],f=window.fetch.bind(window);`
  + `window.__assetURL=u=>A[k(u)]||u;`
  + `window.fetch=(u,o)=>{const s=typeof u==='string'?u:u&&u.url;if(!s)return f(u,o);const key=k(s);return A[key]?f(A[key],o):key.startsWith('assets/')?Promise.resolve(new Response('',{status:404})):f(u,o)}})();`;
const esc = (s) => s.replace(/<\/script/gi, '<\\/script');
html = html.replace(MOD, () => `<script>${esc(shim)}</script>\n<script type="module">${esc(js)}</script>`);
const outFile = path.join(OUT, `${name}.html`);
fs.writeFileSync(outFile, html);

// ---- static gate: a single-file build must not reach the network
const bad = [];
const htmlNoData = html.replace(/data:[^"')\s]+/g, 'data:');
for (const re of [/(?:src|href)="https?:\/\/[^"]+"/g, /url\(https?:[^)]+\)/g, /@import\s+url\(https?:/g, /<script[^>]+src="(?!data:)[^"]+"/g]) for (const m of htmlNoData.match(re) || []) bad.push(m.slice(0, 120));
if (bad.length) fail(`static gate failed, external references remain:\n  ${bad.join('\n  ')}`);
console.log(`wrote ${outFile} (${mb(fs.statSync(outFile).size)})\nwrote ${SITE}/ (code ${tag})\nstatic gate: clean. Now run play-check.mjs against file://${outFile}`);
