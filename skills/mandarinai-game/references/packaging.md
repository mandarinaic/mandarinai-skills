# Packing into one HTML (and a hosted site)

Goal: one HTML that opens by double-click with no server and no network. Reference point
from the upstream project: ≈98 MB of raw assets → ≈21 MB shrunk → ≈30 MB single file. The
starter with two cast members packs to ≈3 MB.

```bash
node scripts/build-single-html.mjs /abs/game --name <slug>
node scripts/play-check.mjs "file:///abs/game/dist/<slug>.html?mute" --shot /abs/packed.png --script /abs/steps.js
```

Build it **mid-project** (Stage 4), not on delivery day, and rerun play-check on the packed
file after every stage from then on.

## Where the size is
Generated models carry 4096 textures (3 MB+ each) plus geometry; rigged characters often
have a second, clip-only file. So:
1. **Textures**: 1024 (hero, boss, big buildings 1536; drops 512), WebP. The biggest saving.
   The builder applies `--tex` to every GLB.
2. **Clip-only files**: clear mesh and skin from every node, then prune with `keepLeaves`, or
   the bones are removed as empty nodes.
3. **Geometry**: decimate at preparation time (prepare-cast does it for the cast). meshopt
   compression saves more but requires shipping the decoder; add it only when size demands.
4. **Ground textures**: 1024.
5. **Music**: re-encoded to ≈96 kbps (`--music-kbps`) when ffmpeg is present.
6. Results are cached by source mtime; rebuilds take seconds.

## Never quantise skinned characters
`meshopt()` quantises vertices by default: it scales the mesh into an integer range and
parks the inverse scale on the armature. Fine for static props; for skinned characters,
height measured from bounds lands in the wrong space, and preset clips carrying `scale = 1`
tracks erase the compensation — the character shrinks the moment it plays. Symptom: "fine in
dev, half size when packed". Characters get `reorder` + `EXT_meshopt_compression` without
`quantize`, and drop `.scale` tracks when loading clips. After packing compare the same
numbers dev vs packed per character (head height, root scale, limb swing while running).

## How inlining works (build-single-html.mjs)
- esbuild bundles `src/main.js` into one minified module, `three` and `three/addons/`
  resolved to the vendored copies.
- Every file under `assets/` becomes a data URL in `window.__A = { "assets/...": "data:..." }`.
- `fetch` is wrapped: a packed path returns its data URL; an unpacked `assets/` path returns
  404 so optional assets (music slots) fail quietly.
- `window.__assetURL` is installed and the game passes it to
  `THREE.DefaultLoadingManager.setURLModifier` (the starter does), so texture and model
  loaders read the table too.
- `<img src>` and CSS `url()` pointing into `assets/` are replaced with data URLs at build time.
- `</script` inside inlined code is escaped.
- A static gate fails the build if any `http(s)` src/href, CSS url, or external script remains.

## Verify the packed file
- play-check on the `file://` URL fails on any request other than the page itself or data/blob URLs.
- Play through at least one full loop (start → key beat → ending): cast, motion, textures,
  UI images, dialogue, sound.
- Ask the user to double-click it on their own machine once; automated browsers do not
  always open local paths the same way.

## Hosted site: draw first, load the rest
`dist/site/` holds the same shrunk assets as separate files plus one hashed module, for
GitHub Pages or any static host — visitors see something before everything downloads.
Order startup by "what is needed for the first frame", not one big `await`:
1. Title image and progress text are in the HTML itself.
2. Pure-code things (sky, ground, grass, weather) build first; start the render loop with a
   pre-game frame function and a slowly drifting camera.
3. Scene models and cast download in parallel; place props as they arrive, growing from the
   ground over a second, staggered near to far.
4. When the cast is in, switch to the real frame function and show "start".
5. Fetch music only after start.
Progress by file count; queue one themed line per file, each shown ≥0.17 s, with small
honest text of what is loading ("立山门 · gate model").

## Mobile and constrained containers
Touch support lives in the game itself, shared by all builds:
- Left half: a floating joystick where the finger lands, feeding an analogue move vector.
  Skill icons become buttons; hold-type buttons release on `pointerup`, `pointercancel`, and
  `pointerleave`. (The starter has tap-to-walk and tap-to-talk; add the joystick for action forms.)
- In touch mode ignore mouse events, or every joystick touch fires a "left-click attack".
- No pointer to aim with: nearest enemy, then joystick direction, then facing.
- Portrait is narrow: widen fov from 38° to ≈50° and pull back (the starter does); bars to
  the top, bottom for thumbs.
- Safe areas: never `var(--x, env(...))`; old engines drop the whole declaration. Resolve
  with script into plain lengths (the starter's head script does).
- Cap the drawing buffer by a pixel budget `min(dpr, 1.5, sqrt(budget / (w×h)))`; on frame
  drops lower resolution, then shadows, bloom, grass. Stop the loop when hidden, handle
  `webglcontextlost`, explain instead of a white screen without WebGL 2.

Platform mini-program containers (e.g. Xiaohongshu mini-tools; read the platform's own spec):

| Limit | Approach |
|---|---|
| No fetch / XHR | rewrite `fetch` at build (esbuild `define`) to a local lookup; data in on-demand classic scripts |
| Only web file types (no .glb / .mp3) | split models into glTF JSON + base64 buffers in .js and assemble a GLB in memory; textures as separate .webp; audio base64 → `decodeAudioData` |
| No WASM | no meshopt/Draco decoders; decimate at build and store normals, UVs, weights as normalised integers (positions stay float) |
| External, non-module scripts | esbuild `format: 'iife'`, `target: ['es2017','chrome61']`, one `<script src>` |
| Package cap (10 MiB) | characters under 10k triangles, textures 512, every other key on long clips, mono low-bitrate music |
| GLTFLoader uses `createImageBitmap` + fetch for textures | define `createImageBitmap` as `undefined` so it falls back to `<img>` |

End such builds with a static scan (forbidden APIs, inline scripts, outbound links,
disallowed file types) and refuse to emit on failure. Working in a browser does not prove it
works in the container: say which parts were only browser-verified.
