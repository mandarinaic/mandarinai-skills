# Effects, drops, UI, copy, volume

## Render base (build it first; everything else only looks expensive on top of it)
Half-float scene buffer + depth → ambient occlusion → volumetric fog sampling the shadow map
(point lights with halos) → multi-level bloom → grade (tone mapping, split toning, vignette)
→ anti-aliasing and light grain. Night: one cool key light plus several warm point lights.
The starter ships the minimal version (ACES tone mapping, soft shadows, fog); grow it in Stage 2.

Weather as particles looping in a box that follows the camera: snow (point sprites), low
mist and wind lines (instanced quads). The whole map has weather; only the camera's
neighbourhood is simulated. The title screen shows the live scene. Ground snow cover via a
noise mask (none on water or steep slopes) — the first version always covers too much.

Chinese-story palettes: ink-wash (水墨) desaturated greens and greys with one accent; 工笔
warm mineral pigments (石青, 石绿, 朱砂); New-Year bright red and gold for festive tales.
Keep brand blue `#1b46a2` and gold `#ffc107` for UI chrome, not the whole world.

## Skill effects: the method
1. **Timing first**: charge → burst → linger and fade. A single "pop" has no weight.
2. **Three ingredients**: a mesh gives shape and path, noise gives detail, a shader scrolls,
   erodes, and colours.
3. **Never a texture on a quad.** That is exactly what users call "stiff, cheap".
4. Burst: a very bright core with soft edges. Ultimates get the most range and layers;
   basic attacks stay restrained.

Recipes:
- **Sword wave (剑气)**: a ring-sector mesh; along the arc a moving head with a decaying
  tail; across the radius a blade profile (bright rim, fast inward falloff, pointed ends);
  scrolling noise streaks; raise the erosion threshold over time so it breaks apart. Under it
  a normally-blended dark ink layer that lives longer. Downward slashes reuse the mesh upright.
- **Magic circle (法阵)**: all in the fragment shader — concentric rings, a rotating rune band
  (polar cells, hash-picked strokes; hanzi-like strokes suit Chinese stories), counter-rotating
  polygons, a reveal expanding from the centre.
- **Falling swords**: real sword meshes (diamond-section blade, tip, guard, grip) plunging at
  an angle with a comet trail; ground crack decal and impact ring; dissolve upward by noise.
- **Telegraphs are effects too**: stripes flowing outward in a cone, a tapering blade for a
  line attack, one bright line for progress. Never flat rectangles or circles.
- **Persistent things** (projectiles, light pillars): cheap crossed quads with scrolling noise.
- Weapons glow while striking; a few rising motes while held. Footsteps kick up dust and leave
  fading prints.

**Bloom is strong: keep HDR colour peaks at 2–3.** The first pass of effects is nearly always
blown out to white; expect two or three brightness passes.

Particles: one fixed-capacity ring buffer is enough. Check the point-sprite size formula; the
default often renders 2–3 pixels.

## Drops and collectibles
- Kills (or story pickups) pop a modelled item up and down; a landing chime.
- Rarity tiers readable at a glance: ring size, pillar height and width, chime pitch and
  length; the top tier gets a sky pillar, landing ring, and periodic pulse.
- Chimes must cut through combat: bell-like, several partials; rarer = higher and longer.
- Auto-collect nearby, then fly along an arc to the bag icon in the corner, which bounces.
  Items must do something.
- The first pillar is always too thin and faint: at least three layers (core, body, wide glow).
- Word collectibles (`learning-layer.md`) follow the same rules: readable hanzi, a pickup
  card, a chime.

## HUD
- **Health bars drawn in code**: thin frame with chamfered ends, gradient fill, bright leading
  edge, ticks, a delayed damage trail. A texture bar is called "looks like a picture" at once.
- Skill bar from the same generated icon set: key labels, cooldown sweep, grey when
  unaffordable, ultimate charge ring.
- Objectives, boss names, banners: serif or kai type, wide tracking, restrained size.
- Hide the HUD during cutscenes (do not let an inline style override that rule).
- Never show "start" before loading has finished.

## Copy
Plain, concrete, little. No shouted move names, no em-dash-and-exclamation narration, no
"PHASE TWO" banners. One opening line stating the goal; a boss says two or three short
story lines; that is enough. Chinese first, translation under it.

## Volume
- Music and ambience far quieter than you think (music ≈ one third of SFX level), or they bury
  the effects.
- Block/parry confirmations are the loudest, crispest sounds: two samples plus a synthesized
  metallic partial.
- Duck the music under speech.
- Synthesized noise wind needs a long loop (seconds); a short one is audibly periodic.
