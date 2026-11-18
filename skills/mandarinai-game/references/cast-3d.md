# The MandarinAi cast in 3D

## What the models are (measured, not assumed)

The 19 characters exist as `.glb` files outside the repo (default `~/Downloads/3D/final/<id>.glb`;
override with `--src` or `MANDARINAI_CAST_3D`). Each source file is:

- **one static mesh — no skeleton, no animations.** Treat them as statues that move as a whole.
- ~180k triangles, Draco-compressed, three 4096 PNG textures (base color, normal, metal-rough),
  `KHR_materials_specular` with factor 2.0 (looks like wet plastic in game light).
- Z-up geometry with a +90° X rotation on the node; after that rotation the model is Y-up,
  feet at 0, facing +Z, and **all ~1.1 m tall** (humans and chibi animals alike).

`scripts/prepare-cast.mjs` turns them into game assets: transform baked, centered, feet on
y=0, facing +Z, rescaled to a per-character game height (`assets/cast-roster.json`: zodiac
1.1 m, humans 1.6–1.75 m), decimated to ~12k triangles (a few with fine detail stay near
20k), textures 1024 WebP, specular extension dropped, Draco removed so no decoder ships.
Typical output 600 KB–1.2 MB per character, ~0.5 s each.

```bash
node scripts/prepare-cast.mjs --out /abs/game/assets/cast rat ox monkey
node scripts/prepare-cast.mjs --out /abs/game/assets/cast --all          # lineup / casting review
node scripts/prepare-cast.mjs --out ... --height 2.2 dragon              # a role-specific size
```

It writes `cast.json` (file, name, kind, height, width, depth, triangles, rigged). Game code
reads sizes from that manifest, never from live mesh bounds, so swapping a model never
changes the feel. Per-role scale (the ox carrying the rat is 1.4×) lives in `story.js`.

If a source model ever arrives with a skeleton, the script keeps it and warns; then follow
`characters-animation.md` and the packaging rule against quantising skinned meshes.

## Casting review

Before building, open `?show=cast` (every prepared character in a row with name and height)
and screenshot it for the user together with the casting table. Model sheets (expressions,
turnarounds, costume detail) are in `../mandarinai-illustration/assets/characters/<id>.jpg`.

| id | Name | Fits roles that are… | Avoid |
|---|---|---|---|
| rat | Rui | clever, quick, the underdog who wins by wit | sneaky thief |
| ox | Bo | steady helper, carrier, patient worker | stupid brute |
| tiger | Kai | brave champion, rival in a fair contest | man-eater (generate a beast instead) |
| rabbit | Lina | gentle companion, 玉兔, first-timer | prey, victim |
| dragon | Wei | wise guardian, 小白龙, rain-bringer | tyrant dragon king |
| snake | Yu | precise planner, riddle-keeper | 白蛇/temptress, villain |
| horse | MaXue | messenger, runner, tireless traveller | war-horse in gore |
| goat | Mei Si | artist, healer, calm counsellor | sacrifice |
| monkey | Xiang | 孙悟空 figure, trickster-hero, explorer | cruel prankster |
| rooster | Ming | herald, dawn-caller, announcer | coward |
| dog | Bao | guardian, loyal companion | attack dog |
| pig | Xin | generous friend, comic warmth | glutton joke, butt of mockery |
| maya | Maya (16) | young traveller entering the story world | ancient-period native (modern clothes) |
| bai | Bai (18) | clever helper, puzzle solver | — |
| yue | Yue (22) | storyteller / guide framing the tale | — |
| amir | Amir (24) | visitor, merchant, diplomat in a frame story | — |
| lian | Lian (26) | host, cook, culture guide (qipao) | — |
| jin | Jin (58) | elder, sage, teacher, 愚公-type answerer | villain |
| grace | Grace (63) | wise elder, grandmother storyteller | — |

The humans wear modern or modern-Chinese clothes. In a period story they work best as a
**frame** (a guide who enters the world, a storyteller), not as period natives. Period
humans (唐僧, 曹冲, 武松) are generated in the house style: concept image → image-to-3D.

## Making unrigged models feel alive (default)

`assets/starter/src/motion.js` animates the whole body: hop-bob on `|sin|`, side roll, lean
into speed, breathing, squash-and-stretch with a damped overshoot on landings and pickups,
per-actor hit flash, per-actor hitstop shake. Chibi proportions read well this way — the
gait of a mascot is a hop, not a stride. Rules:

- Game logic writes only `actor.root` (position, facing); motion writes only `actor.body`.
- Clone materials per actor (the starter does) or one flash lights the whole cast.
- Talking: a small squash per line. Celebrating: `jump()`. Hit: `flash()` + `hitstop()`.
- A held item or weapon attaches to `actor.body` at a measured offset (record it in the
  roster or story, not inline).

## When real animation is needed (upgrade path)

Fighting heroes and anything with limbs that must visibly act (a sword swing, a bow) need a
skeleton. Options, cheapest first:

1. **Image-to-3D platform rigging** (Tripo and similar): upload the character's front/side/
   back renders or the model sheet, generate a rigged model, add preset clips (walk, run, hit,
   fall). Measure each clip's facing and root motion on load (`characters-animation.md`).
2. **Mixamo-style auto-rig** for the humans (humanoid proportions only). The chibi animals
   with big heads and tails rig poorly there.
3. Keep the static model and fake the action with a separate weapon mesh plus a swing
   trail effect (`vfx-ui-audio.md`) — often enough at top-down distance.

Whichever path: the rigged file replaces the static one under the same id, `cast.json`
gets `rigged: true`, and procedural layers stay for squash and flash only.

## Other on-model assets

Portraits for dialogue boxes, title art, icons: generate with `mandarinai-illustration`
using the character sheet as `--ref`; the human cast also has cropped portraits in
`../mandarinai-video/assets/cast/<id>-calm.webp`. Never crop a model sheet into the game.
