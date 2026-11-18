# Assets: models, images, voice, music, sound

## Principles
- Ask which generators and free libraries the user has; read each tool's help and pricing
  command before the first call.
- One look for the whole game: first generate a small set of concept images (each scene
  zone, a prop overview, the UI style) that every later asset follows. Images are cheap.
- Every asset script must be resumable: record each job id and status so a rerun after a
  failure never pays twice. Below a tool's confirmation threshold it charges without asking —
  add up the batch before submitting.
- Keep `assets/SOURCES.md` in the game: one line per file with its source and license.

## The cast
MandarinAi characters come from `scripts/prepare-cast.mjs` (`cast-3d.md`). Do not regenerate
them; on-model consistency is the point of the cast.

## Props and generated characters (image → 3D, e.g. Tripo)
1. **Concept image**: "one single object, fully in frame, plain light-grey seamless background,
   even studio light, no cast shadow, no text, no people, **no glow, particles, or effects**".
   Effects in the image get built as solid geometry.
2. **Image-to-3D**: props on a cheap tier with a face cap (≈5–8k faces); characters from
   multi-view images (front, side, back — check the side view is truly side-on) plus rigging.
3. Small items (drops, weapons) separately; never expect them to be part of a character mesh.
4. Orientation of generated models is arbitrary: measure it. Characters: from hip bones
   (`characters-animation.md`). Weapons: align the bounding box's longest axis.
5. **Period and culture check** before placing: Chinese architecture of the story's era
   (牌坊, 亭, 桥, 城门, 庙 with upturned eaves), not torii, pagodas from elsewhere, or western
   castles. Generated decor frames often drift (western "demonic" ornament for a 仙侠 brief):
   drop them.

Order of magnitude (varies by platform): a prop ≈30 credits; a multi-view character ≈120,
rigging ≈25, each preset clip ≈10.

## Textures and ground
- Ground, rock, soil: full CC0 PBR sets (color, normal, roughness), e.g. Poly Haven.
- Vegetation: instanced meshes you scatter yourself (tens of thousands of blades are fine);
  never place plant models one by one. The starter's grass is the pattern.

## Images for UI
- Skill or item icons: one row of same-style round icons on black in one image, then crop.
  Reuse the exact style prompt when adding icons later.
- Title calligraphy: generate a poster with the calligraphic title, key it out by luminance
  into a transparent layer, lay it over the live scene. Keep the MandarinAi logo as the real file.
- **Never use generated images for health or progress bars**: draw them in code
  (`vfx-ui-audio.md`); a texture bar looks cheap at once.
- On-model character portraits: `mandarinai-illustration` with the sheet as `--ref`.

## Voice
- Mandarin lines: the MandarinAi TTS endpoint used by the video skill —
  `GET https://www.mandarinai.com/tts?text=<url-encoded line>&voice=<Azure voice id>` returns
  `audio/mpeg`. The human cast's voices are fixed in
  `../mandarinai-video/assets/cast/characters.json` (e.g. Yue `zh-CN-XiaoxuanNeural`); for
  zodiac characters pick a zh-CN neural voice by age and temperament and record the choice in
  PLAN.md so it never changes mid-game. No silent fallback: a failed fetch is an error.
- A platform's dedicated voice-design model is next best (≈12 credits a line); a video model
  for the same job costs ≈240 per 12 s. Prompt: `Voice: <age, gender, role, resonance, pace,
  emotion>. No music, no ambience. Line: <line>`. Generate one, check its duration to be sure
  only the line was read, not the description.
- Raw levels are often low. **Normalise peaks to −2 dB first, then trim silence**; trimming
  first cuts quiet words as silence.
- Map subtitle text → voice file in one table; duck the music while anyone speaks.

## Music and ambience
- The user generates music (e.g. Suno); you write the prompts: explore, encounter, finale —
  instruments, mode, tempo, "instrumental, no vocals, seamless loop". Chinese stories:
  guzheng, dizi, pipa, erhu, xiao, percussion; pentatonic.
- Reserve file slots (`assets/music/explore.mp3`…); use the file if present, otherwise a
  simple code-generated bed; crossfade by game state.
- With recorded ambience, switch off any synthesized wind; never stack both.

## Sound effects
- CC0 packs (e.g. OpenGameArt, Kenney), sources logged. Three or more variants per event
  (step, swing, hit, block, pickup, creature call), pick randomly, vary pitch ±5%.
- Synthesis only to fill gaps (UI ticks, low thumps). A "fireball" sample looped as a fire
  crackle becomes harsh noise.
- The starter's `blip()` is a placeholder; replace it before Stage 6 ends.
