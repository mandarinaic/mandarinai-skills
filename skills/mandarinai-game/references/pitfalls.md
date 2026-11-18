# Pitfalls (look up by symptom)

## Game will not open, stuck on "loading", clicks do nothing
- **Read the browser console first**, before suspecting the network. The usual cause is a
  syntax error that stops the entry module from running.
- In long one-line code, never end a line with a `//` comment; it swallows the rest of the line. Use `/* */`.
- `node --check file.js` can miss errors in files with `import`. Use
  `node --input-type=module --check < file.js`.
- Never load libraries from the internet. three.js and its addons are vendored by `new-game.mjs`.
- Opened `index.html` by double-click during development: modules do not load over `file://`.
  Use `serve.mjs`; only the packed single file opens directly.
- `assets/cast/cast.json missing`: run `prepare-cast.mjs` into the game's `assets/cast/`.

## Character drifts sideways, body not over its foot ring
Root motion in a preset clip was not fully removed. See `characters-animation.md`.

## A character is the wrong size or faces the wrong way
- Cast models are normalised to face +Z and stand on y=0 with the roster height. Facing in
  game = `atan2(dx, dz)` on `actor.root.rotation.y`.
- Sizes come from `cast.json` and per-role `story.scale`, never from live bounds.
- Packed build smaller than dev: quantised skinned mesh. See `packaging.md`.

## Keys (the class most likely to get worse with each fix)
- **Hero keeps walking after release / sticks to a wall for seconds**: a key-up was lost
  (holding Cmd or Alt, switching windows) and the key stays in the held set.
  - The fix that works: when a direction is pressed, remove its opposite from the set; clear
    the set on any modifier press/release and on window blur/focus. (`input.js` does this.)
  - The clearing modifiers are Cmd, Alt, Ctrl only — **not Shift**, which games use for
    sprint; including it kills movement while sprinting.
  - **Do not** infer releases from missing auto-repeat: the OS repeats only the last key
    pressed, so the first held key gets dropped ("stops while held", "two keys, one direction").
  - **Do not** poll window focus each frame to clear keys; unreliable in embedded browsers.
- Cannot find it: F3 panel shows held keys, state, speed, focus, last eight key events. Ask the
  user to screenshot it when it happens. **One screenshot tells lost-key from logic bug.**
- Re-sync right-mouse held state from `buttons` on mousemove.
- IME composing (`isComposing`, keyCode 229) is not game input: Chinese learners often have a
  Chinese input method active. `input.js` ignores it.

## Stuck against a wall, cannot move after a transition
- A walkable area was closed with the hero on an island. See `combat-feel.md` → Arena.
- When a collision cannot resolve, revert to last frame's position; never accept an illegal one.

## Scripted tests stall or disagree with real play
- **Flow built on Promises or `setTimeout`**: microtasks and timers do not run between
  `G.step()` calls inside one evaluate, so a dialogue that resolves a promise never hands
  back control. Drive every flow with callbacks and game-time `dt` (the starter's `talk()`).
- Rendering every frame in a headless software renderer is slow (seconds per hundred frames
  with shadows): `G.upd(n)` for long runs, `G.step(1)` only before a screenshot.
- `requestfailed … .glb net::ERR_ABORTED` under Playwright while the model is visibly there:
  three.js re-wraps the response stream; Chromium mislabels it. Non-fatal in play-check.

## Picture
- Effects are a white blob: bloom overexposure; lower colour peaks.
- Grass blades stretched: divide bending by the instance's horizontal scale.
- Camera inside a hill or blocked by a building: `combat-feel.md` → Camera.
- Camera jumps after a cutscene: the cutscene end pose did not match the gameplay camera.
- Hero drifts to the edge of the frame while moving: two smoothing stages on the camera.
- Mascots look like specks: camera too high and far; the starter's offset (0, 6.4, 7.8) at
  38° fov frames a 1.1 m character readably.
- Overlays that fade with CSS transitions do not advance in background tabs: an automated
  black screenshot is not proof of breakage; read computed styles.
- Text toasts piling up: age them in game time, each with its own timer.

## Culture and tone
- A gate that reads as a Japanese torii (lintel overhanging the pillars, second tie beam):
  build or generate a 牌坊 — beams between the pillars, a plaque, a tiled hip roof.
- A MandarinAi character cast as villain, victim, or joke: recast with a generated character.
- Pinyin misaligned, capitalised, or with tone numbers: `learning-layer.md`.

## Testing hygiene
- Hidden tabs do not render: use the stepping hooks.
- Stepped screenshots can be stale: trust state numbers.
- Automated runs make sound: mute by default (`?mute`), return to the title afterwards.
- You may share a browser tab with the user; navigating in it interrupts them.

## Process
- User offered generators, you assembled primitives instead → the whole version is rejected.
- Started without studying the reference → the whole version is rejected.
- Said "done" without looking → the user finds the problem on first open; trust drops.
