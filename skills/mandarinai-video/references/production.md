# Production brief and local pipeline

Run commands from the `mandarinai-video` skill directory. Relative `source`, `image`, `audio`, and `bgm` paths resolve against the brief's directory. `--source` resolves against the current working directory. Use new project directories and output filenames.

## Brief shape

```json
{
  "source": "source.json",
  "mode": "tutorial",
  "format": "portrait",
  "style": "clean",
  "fps": 30,
  "cast": {
    "presenter": "jin",
    "overrides": {"jin": {"voice": "zh-CN-YunyangNeural"}}
  },
  "timing": {"bpm": 96, "beats_per_bar": 4, "snap": "bar", "offset": 0},
  "scenes": [
    {
      "layout": "hero",
      "heading": "Read it in context",
      "text": "今天比昨天热。",
      "pinyin": ["jīn", "tiān", "bǐ", "zuó", "tiān", "rè"],
      "translation": "Today is hotter than yesterday.",
      "narration": "今天比昨天热。",
      "beats": 8,
      "hold": 2,
      "cues": [{"id": "content", "beat": 1}, {"id": "translation", "seconds": 1.5}]
    },
    {
      "layout": "lesson",
      "heading": "Listen and answer",
      "lines": [
        {"speaker": "yue", "text": "今天和昨天，哪一天更热？", "translation": "Which is hotter: today or yesterday?"},
        {"speaker": "maya", "text": "今天比昨天热。", "pinyin": ["jīn", "tiān", "bǐ", "zuó", "tiān", "rè"], "translation": "Today is hotter than yesterday."}
      ],
      "hold": 2
    }
  ]
}
```

This illustrates the schema using the synthetic grammar fixture. Author a real brief against its source. Structure, pinyin counts, and audio duration are checked; claims and pronunciation still need review.

| Top-level field | Meaning |
| --- | --- |
| `source` | Normalized JSON from `prepare-content.py`; overridden by `--source` |
| `mode` | `promo` or `tutorial` |
| `format` | `portrait` (1080×1920), `landscape` (1920×1080), `square` (1080×1080) |
| `width`, `height` | Optional positive even dimensions; recheck layout for a changed ratio |
| `fps` | Integer 1–60; default 30 |
| `style` | `clean`, `editorial`, or `ink` starter palette |
| `title` | Optional title; defaults to source title |
| `cast` | Optional named presenter and explicit voice overrides; see below |
| `timing` | Optional BPM, meter, snapping, and grid offset; see below |
| `scenes` | Up to 24 scenes, each up to 120 seconds |
| `bgm`, `bgm_volume` | Optional local music and relative amplitude; volume defaults to 0.12 |
| `bgm_duck` | Boolean, default `true`; reduces music under speech |

| Scene field | Meaning |
| --- | --- |
| `layout` | `hero`, `lesson`, `facts`, `comparison`, `screenshot`, or `cta` |
| `heading`, `label` | Short heading and optional eyebrow label |
| `text` | Main teaching text; use a short sentence or formula |
| `pinyin` | List or space-separated tone-marked syllables, one per Hanzi in `text`; punctuation excluded |
| `translation` | Learner-language translation; identify a language fallback accurately |
| `bullets` | Short facts, contrasts, or steps |
| `image` | Local image; use a real capture for a screenshot shot |
| `speaker` | Optional known cast ID; defaults to `cast.presenter` |
| `show_presenter` | Boolean, default `true`; hides the presenter strip when `false` |
| `narration` | Voice script for a single utterance; retained in silent drafts |
| `audio` | Local single-utterance recording; takes priority over TTS |
| `lines` | Alternative to `narration`/`audio`: up to four dialogue utterances |
| `duration` | Minimum desired length; never cuts speech short |
| `hold` | Post-speech reading/retrieval time; default 1 second |
| `caption` | Optional single-utterance sidecar caption text |
| `beats` | Optional minimum duration in beats; requires BPM |
| `snap` | Override global `none`, `beat`, or `bar` end snapping |
| `cues` | Named scene-local reveal times, in beats or seconds |

## Cast, portraits, and dialogue

Choose a presenter explicitly for the lesson; this builder does not randomly assign one. The seven human companions and their default voices are recorded in `assets/cast/characters.json`, based on Swan's `utils/characters.ts` and `composables/useVoiceCasting.ts`.

| ID | Character role | Useful production role |
| --- | --- | --- |
| `yue` | Mandarin Learning Guide | Warm welcome, word practice, encouragement |
| `jin` | Grammar & Culture Mentor | Grammar explanation and cultural context |
| `bai` | AI Mandarin Learning Genius | AI/product walkthroughs |
| `lian` | Foodie & Culture Guide | Food and culture lessons |
| `maya` | Beginner Mandarin Learner | Beginner questions and dialogue |
| `amir` | Young Arab Professional Mandarin Learner | Learner dialogue and professional contexts |
| `grace` | Lifelong Mandarin Learner | Learner dialogue and reflective questions |

Named speakers must be in this registry; an explicit unknown speaker fails. Each character keeps the same default voice throughout a project. Use `cast.overrides.CHARACTER_ID.voice` for an explicit permitted Neural voice. `--voice` applies only to an unnamed narrator, so it cannot accidentally give every character one voice. A brief without cast/speakers keeps the original single-narrator behavior.

A scene's `lines` replaces its single `narration`/`audio`. Each line contains `speaker`, `text`, and optional `pinyin`, `translation`, `audio`, or `pause_after`. Pinyin follows the same per-Hanzi rule as scene text. By default there is a 0.35-second gap between lines; the last line has no default gap. An explicit last-line `pause_after` is honored before the scene's `hold`.

Each recorded or synthesized utterance has its own measured file and caption; silent drafts estimate line timing and mark narration as pending. The scene shows the real portrait, speaker name, and a highlight while its recorded line plays. Silent drafts retain portraits and estimated line positions without claiming a speaking voice. Bundled `calm.webp` files are final head-and-shoulder sprites cropped by Swan's character pipeline; they are appropriate production assets. The illustration skill's full model sheets are references for creating new art, not scene portraits. This video workflow currently bundles seven humans, not the twelve zodiac characters.

## Beat grid and reveal cues

`timing.bpm` accepts 20–240. `beats_per_bar` sets the meter (integer 1–12, default 4). `snap` defaults to `none`; choose `beat` or `bar` for rhythmic scene endings. `offset` is the first global beat's time in seconds, from 0 to 10, and defaults to 0. A scene can override `snap` and request a minimum length with `beats`.

The minimum scene duration always includes measured speech, line gaps, and the reading/retrieval hold. Beat/bar snapping only extends its ending to the global grid; it never speeds up a voice or removes pronunciation. Times are rounded up to whole frames so a fractional beat cannot shorten a spoken line or accumulate scene drift.

A cue is `{ "id": "content", "beat": 1 }` or `{ "id": "translation", "seconds": 1.5 }`. Beats are **zero-based and scene-local**: beat 0 is the scene start, regardless of the global grid offset. IDs start with a letter, use letters/numbers/underscores/hyphens, and are at most 64 characters. IDs must be unique within the scene and cue times must lie before its final frame. Frame ceiling converts each cue to a render time.

Generated scenes expose resolved cues through `window.MANDARIN_VIDEO.cues`; each ID maps to `{seconds, frame, beat?}`. Add `data-cue="translation"` (or another matching ID) to reveal an element at that cue. The starter provides cue targets such as `heading` and `content`; custom `renderAt(t)` code can read the same object for more elaborate motion. This is a local contract, not upstream `OM.cue` or forced word alignment.

## Audio and music

Use `--tts` for Swan narration or supply local scene/line `audio`. The endpoint is `/tts`, not `/api/tts`; `--tts-url http://localhost:3000/tts` selects a local Swan origin. Every TTS utterance must fit the 200 JavaScript UTF-16-unit limit. Split long speech at sentence boundaries into lines or scenes. A word's existing `audio` may contain only its pronunciation; chapter audio needs a verified crop before being attached to an excerpt.

Without `--tts`, a spoken script lacking a recording fails. Use `--silent` intentionally for a silent draft; TTS errors never quietly become silence. Projects without narration can be silent intentionally.

The renderer mixes each utterance at its measured offset and pads/trims audio to the full video duration, including the CTA. It fades optional music and ducks it beneath speech by default. Use `bgm_duck: false` only after checking speech remains clear. Captions are measured phrase-level SRT sidecars; forced alignment and burned subtitles are separate work.

To create an original quiet synthesized music bed locally:

```bash
python3 scripts/make-music-bed.py --bpm 96 --bars 32 --out /absolute/task/music.wav
```

The helper generates deterministic instrumental audio and adjacent metadata without samples or network services. Set `bgm` to its output path. Match the brief's BPM and choose enough bars for the full cut. BPM changes the grid and this generated bed; it does not retime imported audio. There is no automatic BPM detection, tempo matching, or time stretching. For supplied music, choose its actual tempo and adjust the timing offset yourself. Learner pronunciation and useful quiet pauses take priority over music.

## Reproducible fixture run

Fixtures carry `_fixture.synthetic: true`. Their links use real library routes; they establish no published lesson, institution, or admission fact.

```bash
python3 scripts/prepare-content.py --kind word --id 900001 \
  --input examples/sources/word.json --out /absolute/task/demo-word-source.json
python3 scripts/build-project.py examples/word-tutorial.json \
  --source /absolute/task/demo-word-source.json --out /absolute/task/demo-word --silent
python3 scripts/render-project.py /absolute/task/demo-word \
  --output /absolute/task/demo-word-v1.mp4
```

Use `--tts` instead of `--silent` for a narrated run against an available Swan TTS service. Other pairs are `grammar.json` + `grammar-tutorial.json`, `university.json` + `university-promo.json`, and `article.json` + `article-tutorial.json`. Demo IDs are in the fixtures. Rewrite samples against a real record for production.

## Outputs and revisions

`project.json` records dimensions, fps, frame counts, scene starts/durations, source metadata, resolved `cast`, and `timing`. Each scene's `voice_tracks` records `{file, speaker, voice, start, duration, caption}`, with scene-local starts; dialogue scenes also retain `lines`. New voice tracks supersede legacy single scene audio when both are present. The renderer continues to accept older manifests containing only one audio file per scene.

`source.json` retains provenance. `script.md` is the edit sheet, `captions.srt` the subtitle sidecar, and `preview.html` a silent seekable view of scenes, portraits, active lines, and cues. Review audible timing and music in the rendered MP4.

The final `NAME.verification.json` records encoded-file checks; `NAME-qa/` contains representative frames. Review actual frames and audio before calling a cut ready. For a revision, identify scene, time, element, and desired change. Rebuild after timing/voice changes so tracks and captions are recalculated, and render to a new versioned filename.
