// Tiny static server for local play: node serve.mjs  (ported from guizang-game-skill, AGPL-3.0)
import http from 'node:http'; import fs from 'node:fs'; import path from 'node:path'; import { fileURLToPath } from 'node:url';
const root = path.dirname(fileURLToPath(import.meta.url)); const port = +process.env.PORT || 5173;
const T = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json', '.glb': 'model/gltf-binary', '.png': 'image/png', '.jpg': 'image/jpeg', '.css': 'text/css', '.webp': 'image/webp', '.mp3': 'audio/mpeg', '.ogg': 'audio/ogg', '.wav': 'audio/wav', '.svg': 'image/svg+xml' };
http.createServer((q, s) => {
  let p = decodeURIComponent(q.url.split('?')[0]); if (p.endsWith('/')) p += 'index.html'; const f = path.join(root, p);
  if (!f.startsWith(root)) { s.writeHead(403); return s.end(); }
  fs.readFile(f, (e, d) => { if (e) { s.writeHead(404); return s.end('not found'); } s.writeHead(200, { 'content-type': T[path.extname(f)] || 'application/octet-stream', 'content-length': d.length, 'cache-control': 'no-store' }); s.end(d); });
}).listen(port, '127.0.0.1', () => console.log('serving ' + root + ' on http://localhost:' + port));
