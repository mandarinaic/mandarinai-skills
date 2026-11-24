---
name: mandarinai-game
description: "Build MandarinAi browser story games or interactive Mandarin learning missions. Use for playable Chinese stories, textbook-to-game adaptations, situation-based dialogue games, or 3D browser games. Learning-first requests use validated lesson objectives and quizzes before scene production; standalone story games can retain pinyin dialogue and word collectibles. Supports Swan integration or an explicitly selected offline HTML build. Lesson authoring alone uses mandarinai-lesson; video output uses mandarinai-video or mandarinai-story-video."
license: AGPL-3.0
metadata:
  version: "0.2.0"
---

# MandarinAi game

<!-- attribution: mandarinai-game is derived from guizang-game-skill by 歸藏 (https://github.com/op7418/guizang-game-skill), AGPL-3.0, see LICENSE. Keep this notice in the skill; never write it into generated games. -->

Turn a Chinese story or book into a small, polished browser game: one or two scenes, a
playable hero, a few characters who talk, a scripted moment, and an ending, packed into a
single HTML that opens offline. The MandarinAi cast plays the roles they fit; the rest of
the world comes from generated or free assets. Brand: name **MandarinAi**, blue `#1b46a2`,
gold `#ffc107`, the real logo files only (never redrawn), signed on the title and end screens.

Failure in this kind of project almost never comes from code that cannot be written. It
comes from nobody having looked at the frame, listened to the sound, or pressed the keys.
The workflow below is built so every stage is seen, heard, or measured before moving on.

`SKILL_ROOT` is the directory containing this file. Run scripts from there after
`npm install` (one time). Game projects live outside the skill, e.g. `./output/games/<slug>/`.

## Choose the route

- **Learning mission, textbook, or assessed quiz:** use `mandarinai-lesson` to author and
  validate the content first, then read [assessment-games.md](references/assessment-games.md).
  Choose a small scene that requires the target language decision. 2D/DOM is appropriate;
  3D, combat, and paid asset generation are optional production choices. The lesson preview
  is a local prototype, not a published Swan activity or an account-mastery service.
- **Story game:** continue with the story workflow below. Dialogue exposure and word
  pickups are useful practice; they do not establish recall or pronunciation mastery.
- **Inside Swan:** preserve Nuxt routing, the activity registry, session ownership, shared
  timer/tween/results, i18n, and CDN delivery. Do not run the offline scaffold over Swan or
  import its global input handlers. The single-file/no-network rules below apply to the
  standalone story build only.

## Step 0 · Agree on five things before writing code

Ask only what the request leaves open; skip what is already answered.

1. **Story and source.** Which story, which episode, and the source text (a public-domain
   classic, a user-supplied book or chapter, a folk tale). Read the text yourself and list
   its beats, roles, and two or three key lines. For long books, `mandarinai-book` can
   deconstruct it first. Rights and adaptation rules: `references/story-adaptation.md`.
2. **Game form.** Pick from the form table in `references/story-adaptation.md` by what the
   story's core action is (journey → exploration; contest → race or challenge; battle →
   top-down action with a boss; wit → puzzle or dialogue choice). Top-down 3/4 view by default:
   far less work than third-person, and it reads more polished.
3. **Casting.** Map each story role to a MandarinAi character when one genuinely fits
   (species, temperament, age); otherwise use a generated character in the same style. Show the
   user the casting table before building. Rules and per-character notes:
   `references/cast-3d.md`.
4. **Learning layer.** On by default for MandarinAi: Chinese dialogue with per-character
   pinyin and a translation line, and the story's own key words as collectibles. Ask the
   level (HSK band) and translation language. Spec: `references/learning-layer.md`. The user
   can switch it off for a pure story game.
5. **Tools and budget.** Which generators are available (image, image-to-3D such as Tripo,
   voice/TTS, music such as Suno) and what each costs. Plug in what the user offers at
   once; do not insist on primitives. Quote before spending, report spend after.

Write the answers, the beat list, the casting table, and a staged plan into `PLAN.md` in
the game folder. Continue within the user's authorized scope; the plan is a reviewable
deliverable, not an automatic confirmation stop. "Research first" from a user is meant
literally: if they give a reference game or video, study it and write down camera, pacing,
and UI observations in that file.

## Stages (each ends with something the user sees)

| Stage | Output | How it is checked |
|---|---|---|
| 0 Plan | PLAN.md: beats, form, casting, learning layer, stages | inspect against the brief |
| 1 Scaffold | `new-game.mjs` project running, cast lineup page | `?show=cast` screenshot |
| 2 World | ground, sky, light, props for each scene | still screenshots before motion |
| 3 Cast in motion | hero controller, NPCs, procedural motion or rigged clips | close-up screenshots + state numbers |
| 4 Story loop | dialogue, objectives, scripted beats, ending | scripted run start→end with G hooks |
| 5 Feel and effects | hit feel, VFX, camera polish (for action forms) | user plays |
| 6 Sound and voice | SFX, music, optional voiced lines | user plays and listens |
| 7 Pack | single HTML + static site | play-check on `file://`, user double-clicks |

At each stage end, write unresolved issues to `TODO.md` in the game folder and keep three
lists apart in your report: **verified** (seen, heard, or measured), **runs without errors**
(not looked at), and **needs the user** (cannot be checked headlessly).

## Scaffold and tools

```bash
cd SKILL_ROOT && npm install                      # once; three.js, gltf-transform, esbuild, sharp, playwright
node scripts/new-game.mjs --out /abs/output/games/<slug> --cast rat,ox
node /abs/output/games/<slug>/serve.mjs           # http://localhost:5173/?auto  (?demo, ?bot, ?show=cast, ?mute, ?god)
```

The starter (`assets/starter/`) is a complete small game — 十二生肖 race with Rui and Bo, a
ferry cutscene, three collectible words, a gate, an end card — wired with every pattern the
references describe. Replace `src/story.js` first, then extend `src/main.js`; do not start
from an empty file.

| Script | Purpose |
|---|---|
| `scripts/new-game.mjs` | copy the starter, vendor three.js (no CDN at runtime), copy the logo, prepare cast |
| `scripts/prepare-cast.mjs` | MandarinAi models → game-ready GLB (Y-up, feet on 0, facing +Z, ~12k tris, WebP), writes `assets/cast/cast.json` |
| `scripts/play-check.mjs` | headless run through the `G` hooks: screenshot, state JSON, fails on page errors or any network request a shipped game should not make |
| `scripts/build-single-html.mjs` | shrink assets, bundle, inline everything → `dist/<slug>.html` + `dist/site/` |
| `assets/starter/src/input.js` | key state that survives lost key-ups, F3 debug panel. Use it; do not rewrite input |
| `assets/starter/src/loop.js` | fixed 60 Hz logic step; a stall drops the backlog instead of taking one huge step |
| `assets/starter/src/autoplay.js` | scripted input queue (hold / press / wait / walk-to) refilled by a game `plan(bot)`: the `?demo` run, and the `?bot` learner (`makeLearner`) |

## Working rules

**Use what exists before making anything.** The cast models, the logo, generated concept art
turned into 3D, CC0 textures and sound packs, user-made music. Primitives and synthesized
sound are placeholders the user will recognise immediately. Asset recipes: `references/assets.md`.

**Image first, then 3D.** Text-to-3D is noticeably worse. Generate a clean concept image
(one object, full frame, plain light-grey background, even light, no effects, no text),
then image-to-3D. Images are cheap; make several and pick.

**Look at every step.** After a shader, a motion, a prop, or an effect: load it in the
browser, step frames, screenshot, zoom in. A syntax check is not a look.

**Culture is content.** Architecture, clothing, props, and calligraphy must be Chinese and of
the story's period: a 牌坊 is not a torii, a 道观 is not a pagoda temple from another
country. Check every generated prop against this before placing it.

**Feedback goes in word for word.** When the user says "the motion is stiff" or "hits feel
weak", look up how the craft solves it (`references/combat-feel.md`,
`references/characters-animation.md`) before turning knobs, and write the finding into PLAN.md.

Read on demand:

- `references/story-adaptation.md` — rights, beat extraction, form table, scope. Before Step 0 ends.
- `references/cast-3d.md` — the 19 characters as 3D: facts, casting fit, motion, rigging path. Before casting.
- `references/learning-layer.md` — dialogue format, pinyin rules, vocabulary, levels. Before writing lines.
- `references/assets.md` — props, textures, images, voice, music, SFX. Before generating any asset.
- `references/characters-animation.md` — rigged clips, IK poses, weight in motion. When a character needs real animation.
- `references/combat-feel.md` — aim assist, hitstop, block/parry, enemy design, camera. Before any fighting.
- `references/vfx-ui-audio.md` — render base, effects, drops, HUD, copy, volume. Before effects and UI.
- `references/pitfalls.md` — symptom index. First stop for any strange bug.
- `references/packaging.md` — single file, hosted site, mobile and constrained containers. By mid-project.

## Verifying without anyone at the screen

Background tabs run no `requestAnimationFrame`, so the game exposes hooks on `window.G`:
`G.step(n)` (logic + render, slow), `G.upd(n)` (logic only, use for long runs), `G.press(code)`,
`G.hold(code, on)`, `G.teleport(x, z)`, `G.advance()` (dialogue), `G.start()`, `G.state()`,
`G.errors`, `G.demo` (`.start()`, `.stop()`, `.running`). URL switches: `?auto` skip title,
`?demo` the game plays itself (any real key or tap takes over), `?bot[=accuracy]&seed=n` a learner
plays it, `?mute`, `?show=cast` lineup, `?god`,
`?paused` (real-time loop off; play-check adds it so screenshots match the printed state).

```bash
node scripts/play-check.mjs "http://localhost:5173/?mute" --shot /abs/shot.png --script /abs/steps.js
```

`steps.js` is a function body with `G` in scope; return what you want printed. `--demo` runs
`G.demo` to its end first and fails if it never finishes. When the story changes, rewrite
`demoPlan()` in `main.js` as the new route (read game state only); a finished demo is the
cheapest whole-story regression, and a live `?demo` run is ready-made trailer footage.

The demo proves the route can be finished; the learner bot shows whether a learner gets
through, and how long it takes. `demoPlan(bot)` gets `null` for the demo and a seeded learner for
`?bot`: the autoplay adds a reaction pause before each decision and lands walks a little off target,
and the plan uses `bot.read(chars)` for reading time and `bot.wrong()` (true at 1 − accuracy) to
take a wrong turn or pick a wrong answer. Every wrong branch must lead back to the route: a river
that stops the hero, a gate that sends them back, feedback and a retry for a wrong answer.

```bash
node scripts/play-check.mjs "http://localhost:5173/?mute" --bot 0.6 --runs 3 --time 60-600
```

Each run uses its own seed in a fresh page, and the report lists game seconds per run. The check
fails when a run never ends (the learner is trapped) or, with `--time`, lands outside the window.
Set the window in PLAN.md from the target session length; tune pacing until accuracy 0.6 sits
comfortably inside it. A seed replays exactly, so a failing seed is a reproducible bug report.

Phones: add `--device phone,phone-landscape,laptop` (instead of `--size`) to any check to repeat it
per device; phones run at dpr 2 with touch emulation and shots get a `-<device>` suffix. On every
device the final screen must fit: text, buttons or images outside the viewport, text drawn over
other text, or a page that scrolls sideways fail the check. It checks the screen the run ends on,
so stop scripts on the busy screens too (the longest dialogue, a quiz with all options, the end
card); `tests/ferry-talk.steps.js` is one. Touch screens get touch wording: keyboard hints carry
`.kbd-only` and their tap version `.touch-only` (both styled in the starter's `index.html`).

Poster / share image: `play-check.mjs <url> --poster <frames> --shot poster.png --size 1200x630`
plays exactly that many demo steps and writes `poster.png.json` (method, frames, sha256, state);
the same frame gives a byte-identical image. Pick the frame by probing `G.state().mode` over the
demo, and hide HUD elements in a steps script when the image is cover art rather than evidence.
`tests/full-loop.steps.js` is a worked example that plays the starter start to finish.
Skill regression (scaffold, play, pack, replay packed): `node --test tests/*.test.mjs`. Rules:

- **Numbers decide, screenshots support.** A frame-stepped screenshot can be stale; state is not.
- Logic runs in **fixed 1/60 s steps** (`src/loop.js`); animate from the game clock `clock`,
  never `performance.now()`, `Date.now()` or `Math.random()` (use the seeded `mulberry32`),
  or stepped runs, the demo and posters stop repeating.
- Honour `prefers-reduced-motion`: non-essential motion (title orbit, pops, shakes) holds still.
- Keep every game flow **synchronous in game time**: dialogue completion, delays, and toasts
  advance with `dt`, never `setTimeout` or Promise chains — microtasks do not run between
  `G.step()` calls, and a promise-driven flow stalls every scripted test.
- Mute automated runs. Return the page to the title when done if sharing the user's browser.
- After any code change, load the page once and read the console; `node --check` misses
  module errors (`node --input-type=module --check < file.js`).
- `ERR_ABORTED` on a `.glb` under Playwright is a known false alarm (three.js re-wraps the
  stream); `play-check` prints it as a warning. A real load failure shows in `G.errors`.

## Reporting

The user reads your report, not your code. Lead with what changed and the current state;
then the three lists (verified / runs without errors / needs the user). If a cause is not
found, say so and give the user a way to capture it (press F3, screenshot the panel). One
good screenshot beats ten rounds of guessing. Report credits spent this round.

## Seven ways these projects go wrong

1. The first version is assembled from primitives and synth beeps, and gets thrown away whole.
2. Motion made by guessing joint angles twists the body. Use whole-body procedural motion for
   unrigged cast, and IK targets (hand, foot, weapon direction) for rigged ones.
3. Effects are a texture slapped on a quad. Use a mesh shaped like the motion, scrolling noise, erosion over time.
4. Player and enemies "fight separately": no aim assist, no hitstop on both sides, no hit tiers, no body collision.
5. Bloom blows effects out to white blobs: keep HDR color peaks at 2–3.
6. A "safety" added to fix one key bug causes the next one. Input does the minimum.
7. Offline and size problems found on delivery day. Build the packager mid-project.

## Constraints

- Generated games never contain the attribution comment above, and never claim to be official
  versions of a book or film. Copyrighted modern works: original game inspired by, no quoted text,
  no copied characters (`references/story-adaptation.md`).
- MandarinAi characters stay on-model and in tone: warm, encouraging, never menacing, never
  killed on screen, never the butt of cruelty. Villains and monsters are generated, not cast.
- No runtime CDN or network: three.js is vendored; the packed HTML makes zero requests.
- Pinyin is lowercase with tone marks, one syllable per hanzi; `dialogue.js` rejects misaligned lines.
- Never deliver a description of a game that was not built and checked. Sizes, counts, and
  "it works" come from the files and the play-check output.
