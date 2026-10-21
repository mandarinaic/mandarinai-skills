# Motion direction and review

## Choose a visual explanation

Borrow the upstream production methods rather than their demo identity. Start with the teaching objective or product action, then choose a representation:

| Task | Useful motion | What to preserve |
| --- | --- | --- |
| Word recognition | Large Hanzi reveal, then pinyin and meaning; repeat in a sentence | Correct tones, word sense, a readable hold |
| Grammar | Move sentence components into a formula; compare a worked pair | Phrase order, role labels, a natural example |
| University introduction | Real campus photo, location, restrained verified facts | Asset source and current factual qualifiers |
| Article comprehension | Ordered quote/excerpt, one vocabulary focus, reveal answer after a hold | Actual wording, punctuation, source context |
| Swan walkthrough | Real UI screenshot with crop/spotlight and sequential action labels | Actual labels, available controls, successful loaded state |

Within each shot, describe what changes: a component joins a sentence, a word gains context, a focus moves to a control. Avoid giving every element an unrelated entrance. Keep one type system and a small color family. Use the bundled MandarinAi logo and existing character assets when needed; do not copy an upstream author's likeness.

The `clean`, `editorial`, and `ink` starter palettes are deliberately small. For more elaborate work, customize the generated HTML with a paused GSAP timeline or direct SVG/canvas drawing controlled by `renderAt(t)`. Retain local assets and a fixed canvas. A still listening, reading, or retrieval beat is valid; continuous motion is not a teaching requirement.

## Plan rhythm before generating frames

Write the learning objective/benefit, audience, language, CTA destination, and a scene list. For each scene note the key event, on-screen text, narration, and reading/practice hold. Decide the hook, central explanation, densest view, and ending before rendering. A promo can emphasize fewer ideas than a lesson.

Do not force narration into a guessed 30-second cut. Measure it, then set the visual holds and regenerate captions. For a pronunciation lesson, leave a repeat-after-me pause and prioritize speech over music. Fact-heavy university clips need longer reading time than a word reveal.

For a comparison scene, distinguish semantic differences with labels as well as color. For grammar formulas, animate phrase groups rather than scattering individual glyphs. Do not present an invented ungrammatical example as source material; label it as a teaching contrast and verify the correction.

## Presenters, dialogue, and musical rhythm

Cast a character to support the teaching objective: Jin can explain a grammar rule while Yue and Maya demonstrate it; Bai suits an AI/product walkthrough. Use the bundled human registry and cropped portraits so face, name, and voice stay consistent. Keep dialogues short enough to read; the active portrait and highlighted line identify who speaks, without relying on voice alone.

Use `timing` to plan a beat grid and scene `cues` to coordinate a reveal with a beat. Beat indices in cues start at 0 relative to the scene. The builder resolves them to numeric frame times in `window.MANDARIN_VIDEO.cues`. A scene ending may snap to a global beat/bar after measured narration and holds, but a beat never shortens a pronunciation or retrieval pause.

A quiet original synthesized bed can come from `scripts/make-music-bed.py`. This helper is a small deterministic instrumental generator, not an upstream music studio or a general music composer. For a local supplied track, match its BPM and offset yourself; no tempo detection or stretching occurs. Keep music low and duck it during speech. Review the final mix on a phone as well as headphones.

## Determinism and targeted revisions

Each starter scene exposes `window.renderAt(seconds)` and declares `data-duration`. Its rendered state must depend only on the requested time and fixed input, including when seeking backwards. For custom code, reset every animated property on each seek, use seeded variation if needed, and avoid `Date.now()`, unseeded randomness, media playback, or incremental simulation in this mode.

For a complex custom animation, compare direct seek to a mid-shot time, sequential playback to that time, and a seek back from the end. These must show the same semantic state. Keep a stable scene identity and record revision requests as scene + timestamp + visible element + desired change. A timing change requires rebuilding the manifest and audio/captions, not just extending the HTML.

This pipeline implements its own numeric cues, beat grid, and small synthesized music-bed helper. It does not implement upstream `OM.cue`, `OM.sfx`, studio inboxes, a general music composer, the 35-art-style catalog, or the nine art-fragment grammars. Do not invoke those APIs in a project that only includes this skill. If the user requests an upstream runtime, inspect its current contract and dependencies and keep its project separate.

## Review the evidence

1. Check every source-dependent claim, pronunciation, translation, and HSK label against the snapshot. Read it as a student would. Synthetic fixtures are demos, never production facts.
2. Inspect first content, densest content, and CTA frames, plus scene transitions. Verify CJK/tone-mark glyphs, ruby spacing, safe areas, contrast, and no clipping. Change portrait layouts when making landscape/square outputs.
3. Watch the full cut at normal speed and listen to the start/end of spoken lines. Check each character keeps the expected face/voice, dialogue gaps feel natural, active highlights follow speech, and music ducking preserves intelligibility. A clip must allow reading and practice; empty time and useful pauses are different.
4. Check SRT cue order against narration and explicitly label timing precision. A measured phrase does not imply word-level alignment. Sidecar captions are not burned captions.
5. Read the actual encoded-file verification: H.264/yuv420p dimensions, frame rate/count, total duration, expected AAC audio, and audio coverage through the final CTA. Do not substitute a command's success status or a review file's existence for findings.

Record remaining defects and the exact output version reviewed. Do not label a silent draft as narrated or a prepared HTML project as a rendered MP4.

## Upstream references and limits

Inspected revisions: `huashu-motion` `5f2608c2e12abcf518f74dde86093b19f7f88603`; `huashu-art-motion` `8a0d7d72ca65fcce6f8ba82c4a6c8dfe35b8422c`.

- [Motion workflow](https://github.com/alchaincyf/huashu-motion/blob/5f2608c2e12abcf518f74dde86093b19f7f88603/skills/huashu-motion/SKILL.md): product understanding, a coherent direction, timed scenes, local review.
- [Motion composition contract](https://github.com/alchaincyf/huashu-motion/blob/5f2608c2e12abcf518f74dde86093b19f7f88603/skills/huashu-motion/references/contract.md) and [runtime](https://github.com/alchaincyf/huashu-motion/blob/5f2608c2e12abcf518f74dde86093b19f7f88603/runtime/om.js): paused compositions and deterministic clocks. These are distinct from this skill's `renderAt` contract.
- [Motion voice implementation](https://github.com/alchaincyf/huashu-motion/blob/5f2608c2e12abcf518f74dde86093b19f7f88603/cli/lib/voice.js): alignment precision varies; its Chinese Kokoro/espeak path lacks tones. Use verified Mandarin audio instead for pronunciation lessons.
- [Art capture](https://github.com/alchaincyf/huashu-art-motion/blob/8a0d7d72ca65fcce6f8ba82c4a6c8dfe35b8422c/scripts/engine/render.py): art specs/custom `renderFrame(t)` scenes use a separate runtime. Word cues must become numeric timestamps before art specs can use them.
- [Motion QA](https://github.com/alchaincyf/huashu-motion/blob/5f2608c2e12abcf518f74dde86093b19f7f88603/cli/lib/qa.js), [art QA](https://github.com/alchaincyf/huashu-art-motion/blob/8a0d7d72ca65fcce6f8ba82c4a6c8dfe35b8422c/scripts/qa.py), and [art delivery](https://github.com/alchaincyf/huashu-art-motion/blob/8a0d7d72ca65fcce6f8ba82c4a6c8dfe35b8422c/scripts/deliver.py): inspect reported findings, not only exit status. Cinematic motion heuristics need interpretation for educational holds.
- [Motion third-party notices](https://github.com/alchaincyf/huashu-motion/blob/5f2608c2e12abcf518f74dde86093b19f7f88603/THIRD_PARTY.md) and [art license](https://github.com/alchaincyf/huashu-art-motion/blob/8a0d7d72ca65fcce6f8ba82c4a6c8dfe35b8422c/LICENSE): upstream code/docs MIT; some runtime libraries, fonts, samples, and likenesses have separate terms. No upstream runtime/assets are bundled by this update. Existing Apache notices on this skill's original renderer/templates remain applicable.
