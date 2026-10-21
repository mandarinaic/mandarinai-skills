---
name: mandarinai-video
description: "Generate MandarinAi promo or tutorial MP4s for HSK words, grammar, universities, and processed articles from Goose data and Swan pages. Use for 宣传片、教程视频、语法讲解、词汇教学、大学介绍、文章解读, product walkthroughs, launch clips, or animated HTML scenes. Includes named MandarinAi presenters and dialogue, beat timing, quiet music, editable previews, narration, subtitles, and local rendering. Sentence-by-sentence graded-story read-alongs use mandarinai-story-video; fetching existing videos uses mandarinai-video-fetch."
metadata:
  version: "0.3.0"
---

# MandarinAi video

Turn project content into a watchable promo or teaching video, with source records, an editable project, captions, and a verified MP4. Keep the MandarinAi name, real bundled logo, blue `#1b46a2`, and yellow `#ffc107`.

The motion direction draws on [huashu-motion](https://github.com/alchaincyf/huashu-motion) and [huashu-art-motion](https://github.com/alchaincyf/huashu-art-motion). This skill runs its own HTML/Playwright/FFmpeg pipeline; it does not require either upstream runtime. Existing Apache-2.0 render/template attribution remains in place.

## Choose the route

- **Project promo/tutorial**: use the content workflow below. Default promo: 20–35 seconds, one benefit and one CTA. Default tutorial: 40–75 seconds, one learning objective, worked example, and recall beat. Use 9:16 for short-form social; 16:9 for a desktop walkthrough; 1:1 when requested. Defaults are starting points; let narration and reading time determine the actual length.
- **A word page's existing export**: Swan supports strokes, examples, relations, quizzes, presenters, and narration. Use the real page/export control when that is the requested result. See [project-content.md](references/project-content.md); browser output format depends on encoder support.
- **Sentence-by-sentence graded story**: use `mandarinai-story-video`. For a processed article, obtain the source first with this skill's helper, then select its sentences for the story input.
- **Standalone title, chart, or HTML scene**: retain the standalone scene workflow below.

Use available IDs, links, exports, and preferences. When an ID is missing, search the real project list endpoint or use the supplied local export. Choose routine production defaults and proceed; never invent a published record to fill a gap.

## 1. Obtain the actual content

Read [project-content.md](references/project-content.md) for the relevant Goose endpoint, Swan route, locale, and data shape. `SKILL_ROOT` means the directory containing this file; run commands from there. Store generated work in a task output directory such as `./output/videos/<slug>/`, outside the skill installation.

```bash
python3 scripts/prepare-content.py --kind word --id REAL_WORD_ID \
  --language en --out /absolute/task/source.json
```

Kinds are `word`, `grammar`, `university`, `article`. Use `--input saved-response.json` for an existing authorized export. `--api-base` / `MANDARIN_API_BASE` selects Goose's public origin; `--site-base` / `MANDARIN_SITE_BASE` selects Swan's origin. Defaults use `https://www.mandarinai.com`. The helper saves provenance and the original record alongside readable fields. It refuses to replace an existing snapshot.

Inspect `content` and `raw` before scripting. Keep structured example order, translations, article punctuation and content blocks, university locations, and the difference between missing facts and negative facts. Examples under `examples/sources/` are synthetic fixtures; their links lead to library pages and must never be represented as published records.

For a UI walkthrough, capture the real resolved Swan page after its content, fonts, and images load. Save screenshots locally and record their URLs in the script. Only claim interactions the current UI supports. Explanatory motion graphics should be visibly distinct from UI captures.

## 2. Write the production brief

Read [production.md](references/production.md) for the schema and commands, and [motion-direction.md](references/motion-direction.md) for pacing, explanation techniques, and review. Choose one visual direction; offer alternatives when requested. A reviewable storyboard and preview are deliverables, not a mandatory approval stop.

Write `brief.json` with `mode`, `format`, `style`, and `scenes`. Use one claim or learning step per scene. Select a named presenter explicitly: Yue for a warm learning guide, Jin for grammar/culture, Bai for AI/product help, or Lian for food/culture. Maya, Amir, and Grace can join as learner dialogue partners. The local cast registry and real cropped Swan portraits are bundled under `assets/cast/`; keep a character’s face and voice consistent. The four sample briefs show useful narrative shapes:

| Source | Tutorial | Promo |
| --- | --- | --- |
| HSK word | Meaning → pronunciation/example → retrieval → word-page CTA | Recognizable need → real word features → CTA |
| Grammar | Meaning → formula → worked example → recall | Learning difficulty → useful construction → examples → CTA |
| University | Place → verified facts → how to explore programs | Institution → verified highlights → details CTA |
| Processed article | Context → ordered excerpt → vocabulary/grammar → comprehension | Hook → excerpt → reader controls → article CTA |

Use the record's pinyin, meaning, translation, and HSK level where available; check polyphonic readings before narration. Per-Hanzi ruby needs one tone-marked syllable per Hanzi; use natural word-level pinyin separately when ruby is inappropriate. HSK internal level `7` is displayed as `7–9`. Do not assert a whole example is at a level merely because its target word is.

Use `cast: {"presenter":"jin"}` and optional scene `speaker`; for a conversation use up to four `lines` with named `speaker`, `text`, and optional pinyin/translation. Each utterance gets a measured voice track, caption, portrait, and active-speaker highlight. Unknown named speakers fail; never infer a new voice from a name. See the production reference for stable voice overrides.

Prefer existing suitable audio, a local recording, or Swan's `/tts` for intelligible Mandarin narration. Do not substitute an unverified voice model for pronunciation teaching. Scene timing comes from measured audio plus a reading/retrieval hold. Optional `timing` adds BPM and beat/bar boundaries; snapping only extends a scene after speech and holds. Use scene `cues` for frame-resolved reveals. These cues use this skill’s `renderAt` contract, not upstream `OM.cue`. Character highlights without alignment are approximate; generated SRT has phrase-level timing.

## 3. Build and preview

```bash
python3 scripts/build-project.py /absolute/task/brief.json \
  --source /absolute/task/source.json --out /absolute/task/project --tts
```

`--tts` uses Swan `/tts?text=...&voice=...`, keeping upstream credentials on Swan. Use `--tts-url` for a local Swan origin. Each line must fit its 200 UTF-16-unit limit. Local scene/line `audio` also works. Named voices come from the cast registry or explicit `cast.overrides`; `--voice` affects only an unnamed narrator. If narration is unavailable, fix it or explicitly build a silent draft with `--silent`; the manifest records this choice. Do not quietly drop failed audio.

The builder creates self-contained scene HTML, a seekable `preview.html`, `project.json`, `source.json`, `script.md`, `captions.srt`, and local assets. The preview is silent; seek it to inspect dialogue, portraits, and cue reveals, then review audio in the rendered MP4. Inspect the first content scene, the densest scene, and the CTA in the preview. Rebuild into a new directory after brief changes. Starters support `clean`, `editorial`, and `ink` palettes plus hero, lesson, facts, comparison, screenshot, and CTA layouts. For bespoke motion, edit the generated scene and preserve `window.renderAt(seconds)`.

Optional `bgm` uses a local track, with fades and speech ducking by default. For an original quiet synthesized bed, run `python3 scripts/make-music-bed.py --bpm 96 --bars 32 --out /absolute/task/music.wav`, then reference that file in the brief. Choose matching BPM/offset for imported music; the pipeline does not detect or stretch its tempo. Prioritize clear learner audio. Captions are a sidecar, not burned into the video; learning text remains visible in the scenes.

## 4. Render, review, deliver

```bash
python3 scripts/render-project.py /absolute/task/project \
  --output /absolute/task/tutorial-v1.mp4
```

The renderer captures scenes at exact frame times, concatenates them, mixes narration/music through the full CTA, and verifies the file with `ffprobe`. Optional `--browser /path/to/chrome` uses an installed executable. Existing outputs are preserved; use a new versioned filename.

Inspect adjacent `*.verification.json` and representative frames under `*-qa/`. Review the full cut for meaning, pronunciation, reading time, transitions, and audio balance. Machine checks cannot certify instructional accuracy or every layout. Use [motion-direction.md](references/motion-direction.md)'s criteria and record unresolved issues. If a shot clips text, simplify or split it and render again.

Deliver the MP4, captions, project/preview, source provenance, and actual duration/resolution/audio status. State whether captions are sidecar-only and whether audio is synthesized, local, or absent. If rendering fails, explicitly say **MP4 was not rendered**, include the editable project and exact rerun command, and report the concrete missing dependency.

## Standalone HTML scenes

The original six templates remain available: [templates.md](references/templates.md). Read [authoring.md](references/authoring.md) before writing a scene. Copy a template to the task output folder and replace its content; the logo must use the actual `assets/brand/` PNG.

```bash
node scripts/render.mjs -o /absolute/task/title-v1.mp4 scene1.html scene2.html
```

`-d` sets a shared explicit duration; `-s 1080x1920` sets portrait output; `-f 30` sets fps. This low-level command outputs silent video. Use the project workflow for mixed narration/music. Legacy CSS/GSAP uses virtual time in default `frames` mode; real `<video>` needs `-c screencast`. Seekable scenes instead expose `window.renderAt(t)` and `data-duration` (see authoring reference).

## Dependencies and boundaries

Node, Python 3, Playwright, FFmpeg/ffprobe:

```bash
npm install
npx playwright install chromium
```

FFmpeg must be on PATH. New project scenes use local assets and system CJK fonts, with no CDN dependency; older templates may fetch Google Fonts/Tailwind. Check the environment and use existing Chrome via `--browser` when appropriate. When rendering is unavailable, deliver the project honestly; do not promise an MP4 from an untested fallback.

Generation reads Goose and renders locally. Publishing, uploading, changing article visibility, or changing Goose/Swan code is outside this workflow unless requested. Assets, screenshots, and narration belong in the task project; keep API keys out of briefs, HTML, and delivery files.
