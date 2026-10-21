# Production brief and local pipeline

Run commands from the `mandarinai-video` skill directory. Relative `source`, `image`, `audio`, and `bgm` paths in a brief resolve against the brief's directory. `--source` overrides `source` and resolves against the current working directory. Project directories and output filenames must be new.

## Brief shape

```json
{
  "source": "source.json",
  "mode": "tutorial",
  "format": "portrait",
  "style": "clean",
  "fps": 30,
  "scenes": [
    {
      "layout": "hero",
      "heading": "会用这个词吗？",
      "text": "学习",
      "pinyin": ["xué", "xí"],
      "translation": "to study; to learn",
      "narration": "今天，我们一起学习这个词。",
      "duration": 4
    },
    {
      "layout": "lesson",
      "heading": "Read it in context",
      "text": "我学习中文。",
      "pinyin": ["wǒ", "xué", "xí", "zhōng", "wén"],
      "translation": "I study Chinese.",
      "narration": "我学习中文。",
      "hold": 2
    },
    {
      "layout": "cta",
      "heading": "Keep learning with MandarinAi",
      "text": "Open the source page to practise."
    }
  ]
}
```

This illustrates the schema; a real brief must use its source's actual words, examples, or facts. The builder checks structure, pinyin counts, and audio duration. It cannot establish whether a claim or pronunciation is correct.

| Field | Meaning |
| --- | --- |
| `source` | Normalized source JSON from `prepare-content.py`; can be overridden with `--source` |
| `mode` | `promo` or `tutorial`; documents the production intent |
| `format` | `portrait` (1080×1920), `landscape` (1920×1080), `square` (1080×1080) |
| `width`, `height` | Optional positive even dimensions for previews or custom canvases; recheck layout after changing ratio |
| `fps` | Integer 1–60, default 30 |
| `style` | `clean`, `editorial`, `ink`; starter directions, not copies of upstream art styles |
| `title` | Optional project title; defaults to source title |
| `scenes` | Up to 24 scenes, each up to 120 seconds; split longer lessons |
| `bgm`, `bgm_volume` | Optional licensed local music; relative amplitude defaults to 0.12 |

Per scene:

| Field | Meaning |
| --- | --- |
| `layout` | `hero`, `lesson`, `facts`, `comparison`, `screenshot`, `cta` |
| `heading` | Short on-screen heading |
| `text` | Main teaching text; one short sentence or formula per scene |
| `pinyin` | Optional list or space-separated syllables, one per Hanzi in `text`; punctuation excluded; tone numbers rejected |
| `translation` | Learner-language translation; label any language fallback accurately |
| `label` | Optional short eyebrow label |
| `bullets` | Short facts, contrasts, or steps; split long lists |
| `image` | Local image; use a real capture for a screenshot shot |
| `narration` | Voice script; retained in a silent draft |
| `audio` | Local recording/appropriate source audio; takes priority over TTS |
| `duration` | Minimum desired scene length, expanded when narration requires more time |
| `hold` | Post-narration reading/retrieval time, default 1 second |
| `caption` | Optional sidecar cue text |

## Audio and synchronization

The builder places narration after a short visual lead, probes each file with `ffprobe`, then rounds scene duration up to a whole frame. `duration` never cuts a spoken line short. `hold` provides pronunciation repetition and retrieval time; such holds may be visually still.

Use `--tts` to fetch narration from Swan, or provide scene `audio`. The endpoint is `/tts`, not `/api/tts`. A local environment can use `--tts-url http://localhost:3000/tts`; `--voice` selects a permitted Neural voice. Article read-along audio may cover a whole chapter: crop to a verified sentence interval before attaching it to an excerpt. A word's existing `audio` may be only its pronunciation, not the full narration script.

Without `--tts`, narration lacking a recording fails. For an intentionally silent draft, pass `--silent`. A TTS/network error fails rather than switching to silence. Projects without narration can be silent intentionally.

The renderer combines delayed narration and optional music, pads/trims to the **full video duration**, and encodes AAC. The CTA remains visible after narration. `captions.srt` has phrase-level cues; the pipeline does not perform forced alignment or burn captions. Add alignment if verified karaoke timing is requested.

## Reproducible fixture run

Fixtures carry `_fixture.synthetic: true`. Their links use real library routes; they do not establish a live record, institution, or current admission fact.

```bash
python3 scripts/prepare-content.py --kind word --id 900001 \
  --input examples/sources/word.json --out /absolute/task/demo-word-source.json
python3 scripts/build-project.py examples/word-tutorial.json \
  --source /absolute/task/demo-word-source.json --out /absolute/task/demo-word --silent
python3 scripts/render-project.py /absolute/task/demo-word \
  --output /absolute/task/demo-word-v1.mp4
```

Other pairs: `grammar.json` + `grammar-tutorial.json`, `university.json` + `university-promo.json`, `article.json` + `article-tutorial.json`. Demo IDs are in the fixtures. For real work, prepare a real record and rewrite sample claims against it.

## Output and revision

`project.json` records dimensions, fps, starts/frame counts/durations, audio, and source metadata. `source.json` retains the snapshot. `script.md` is the narration/edit sheet; `captions.srt` is the subtitle sidecar. `preview.html` selects and seeks a scene to locate feedback timestamps.

The final `NAME.verification.json` records encoded-file checks. `NAME-qa/` contains representative frames. Review actual frames and audio before calling the video ready. A successful subprocess cannot certify readability, teaching quality, factual grounding, or every frame.

For feedback, identify the scene and timestamp, update the brief or generated HTML, and render to `-v2.mp4`. Keep previous outputs. Duration changes require rebuilding so captions and narration offsets are recalculated.
