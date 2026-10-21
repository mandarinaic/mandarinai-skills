# MandarinAi project content for video

Use Goose records as teaching sources and Swan as the real product interface.
This skill creates local production files; it does not add a Goose video API,
change Swan, publish videos, upload assets, or alter source records.

## Prepare one source record

Run from the skills repository, replacing IDs with records actually selected:

```bash
python3 skills/mandarinai-video/scripts/prepare-content.py \
  --kind word --id 123 --language en --out output/source.json
```

Kinds are `word`, `grammar`, `university`, and `article`. For an existing response
file, including a user-supplied private article export, use the offline path:

```bash
python3 skills/mandarinai-video/scripts/prepare-content.py \
  --kind article --id 123 --input response.json --out output/source.json
```

`--input` avoids network fetching. `--api-base` / `MANDARIN_API_BASE` selects
Goose; `--site-base` / `MANDARIN_SITE_BASE` selects Swan. Both default to
`https://www.mandarinai.com`. Local Goose normally runs at
`http://localhost:40002`; discover the actual Swan dev URL before linking it.
Do not assume the Goose API origin also serves the frontend.

The helper reads a bare detail object or a successful Goose envelope
`{"code":200,"message":"...","data":{...}}`. It does not unwrap `data.result`
or choose a record from `list`: supply the detail response, not a search page.
Swan's `useHttp*New` composables already unwrap `data`; raw HTTP responses do not.

The normalized file has `kind`, `id`, `title`, `url`, `language`, `captured_at`,
`content`, `raw`, and `provenance`; API captures also have `api_url`.
`raw` preserves the source detail record. `content` retains useful canonical
fields, with normalized word `examples` and university `gallery` for authoring.
`provenance.method` is `file` or `api`; file provenance retains the input
basename. `visibility` is `public`, `private`, or `unspecified`. Keep this
provenance when preparing scenes; a local export is not evidence of public access.

`examples/sources/{word,grammar,university,article}.json` are synthetic fixtures.
Their `_fixture.synthetic` marker becomes `provenance.synthetic`; their links
point to real list/library routes, not invented detail records. Label fixture
renders as demos. They do not establish live records, counts, or product results.

## Read-only endpoints and landing pages

| Kind | Goose GET detail | Swan landing page |
| --- | --- | --- |
| word | `/api/word/hsk/get?id=ID&language=LANG&include=examples,download,relations,quiz` | `/hsk/word/detail/ID` |
| grammar | `/api/grammar/get?id=ID` | `/grammar/detail/ID` |
| university | `/api/university/get?id=ID` | `/university/detail/ID` |
| article | `/api/article/processed/ID?lang=LANG` | `/tools/articles/ID` |

Swan also sends `language=LANG` for multilingual grammar detail. Preserve all
available translations and resolve the requested language rather than guessing
that the legacy `english` field is the teaching title.

To discover IDs, use the corresponding GET lists:
`/api/word/hsk/list`, `/api/grammar/list`, `/api/university/list`, and
`/api/articles/processed`, with `page` and `limit` (and supported filters).
The helper prepares one supplied ID; it does not choose or create content.
Fetch public content without account credentials. Do not fetch a private article
through this public path or reuse browser cookies to bypass its visibility.
Authorized private article files may be used locally with private provenance.

Swan uses locale prefixes: English is unprefixed; the other supported locales
are `/es`, `/fr`, `/ar`, `/ru`, and `/zh`. Thus a French word link is
`/fr/hsk/word/detail/ID`, not `/en/...` or a hand-written `?lang=fr` UI link.
Use these verified list/library fallbacks if no detail URL has been verified:
`/hsk/word/list/1`, `/grammar/list/1`, `/university/list/1`, `/tools/articles`.
Processed articles are not the separate legacy `/article/detail/ID` content type.

## HSK word lesson or promo

- Core fields: `word`, `pinyin`, `english`, `meaning`, `meanings`,
  `hsk_level`, `part_of_speech`, `word_t`, `zhuyin`, `audio`, `image`.
  Use wire field `hsk_level`; the older frontend type's `level` is incomplete.
- Prefer `structured_examples`: each has `chinese`, `pinyin`, optional `audio`,
  and a `translations` object keyed by language. Localize to the requested
  language, then English, and identify fallback copy. Legacy `examples` can be
  HTML, not an array of sentences; strip markup and review before narration.
- Show relevant published `synonyms`, `antonyms`, `homographs`, `measure_words`,
  or `meaning_quiz_options` only when present. Preserve relation labels and the
  quiz answer; do not invent distractors and claim they came from the database.
- Internal level `7` represents HSK 7–9. Preserve source pinyin and verify tone
  marks, polyphonic characters, and hanzi alignment. Do not replace pronunciation
  with the traditional recognition form or narrate English glosses as Chinese.
- A short tutorial can show the real word header, pronunciation, stroke order,
  examples, export menu, and study-plan action. Account actions require the
  appropriate signed-in demo state; showing a button does not prove it succeeded.
- `/api/word/hsk/download` returns JSON for download preparation, not MP4 bytes.
  Goose has no general video-render endpoint for this offline skill.

## Grammar lesson or promo

Use `title`, `english_title`, `hsk_level`, `images` (legacy `image` fallback),
`audio_url`, and especially `content_groups`. Respect group and sentence `order`.
Groups contain `id`, `title`, `en_title`, and `sentences`; sentences contain
`chinese`, `pinyin`, and `translations` entries with `language` / `translation`.
Chinese sentence fields may contain editorial HTML: sanitize/strip it before
placing plain text into captions or narration. Keep intended emphasis separately.

Use the first ordered usage group for the lesson explanation; use its examples
to demonstrate the pattern. `abstract` and legacy HTML `content` are fallbacks.
English UI titles prefer `english_title`; `english` is a legacy example/gloss.
A tutorial can capture the real group navigation (`#group-ID`) and audio player.
Any new mistake/correction example must be reviewed and labeled as authored copy,
not silently attributed to the source record.

## University discovery promo or tutorial

Use actual `name`, `en_name`, `logo`, `alias`, `funding`, `founded_year`, `intro`,
`website`, `admission_url`, `degree_levels`, and location objects (`city`,
`province`, `country`). Do not rely on the older simplified `University` type
using `name_en` or string locations. Combine `images` with `campuses[].images`,
deduplicating in display order; retain campus names as photo provenance.

Show only evidenced facts. A missing HSK admission requirement is unknown, not
“no HSK required”; missing tuition, deadlines, ranking, or scholarship data are
also unknown. Dates and admission claims need current official evidence before
being presented as current advice. Never imply guaranteed admission or funding.

Swan's page has `#about`, `#majors`, `#scholarships`, `#programs`, and `#files`.
Extra pages use `/university/detail/ID/{majors|scholarships|programs}/PAGE`.
Degree/program data are separate endpoints (`/api/university/ID/degrees` and
`/api/university/ID/programs`); a detail-only capture is not a complete catalog.

## Processed article reading lesson or tutorial

Use `title`, `chinese_text`, `original_text`, `thumbnail`, `sentences`,
`content_blocks`, and `metadata`. Metadata can include `recommended_hsk_level`,
`total_characters`, `estimated_difficulty`, and `estimated_reading_time`.
Keep image/text block order and sentence order. Do not confuse English-source
`original_text` with the Chinese text the learner will read.

Each sentence's `word_segments` preserves words, spaces, and punctuation. A flat
`segments` array may also exist. Do not join only HSK words and lose the sentence.
Resolve sentence translations by language; do not fabricate absent annotations.
Segments may identify an HSK word without its meaning: enrich via
`/api/word/hsk/batch?ids=ID1,ID2&language=LANG` (up to 100 IDs per request).

The real reader supports Reading Options, pinyin, translations, learning mode,
paragraph mode, HSK-level toggles, sentence audio, and vocabulary collection.
Processing at `/tools/article-processor` requires login; segment editing is
author-only. Prefer an existing public article for captures. Do not start new
processing jobs, edit segments, save progress, or collect vocabulary merely to
fetch data for a video.

## Genuine product capture and reusable assets

Record the selected record URL, locale, viewport, and capture time with each UI
shot. Load real content, wait for fonts/images, and inspect the final screenshot
for loading/error states. A hand-built teaching card is fine as a motion scene;
it must not be presented as a screenshot or proof of a product feature.

Swan's `public/logo.png`, `logo-dark-bg.png`, and `logo-white-bg.png` are real
brand assets; this skill's bundled `assets/brand/` remains the production source.
Brand blue is `#1b46a2`. CJK fonts include Noto Sans SC and PingFang SC. Resolve
relative image storage keys as `https://i.cdnl.ink/KEY` (Swan `formatImage`);
retain absolute URLs. Reuse real university photos and SVG mascot assets rather
than making up campus evidence, logos, or product screens.

## Existing Swan export versus local production

Swan already exports individual word videos through `components/Words/Export.vue`
and `VideoGenerator.vue`, using `useWordVideoGenerator`, `useVideoComposition`,
and `useVideoExport`. It supports strokes, examples, relations, quizzes,
presenters, narration, and 9:16 / 16:9 / 1:1. MP4/WebM availability depends on
the browser. This skill prepares a separate local project for broader promos
and lessons; it does not automatically install that workflow in Swan or Goose.

Swan word narration uses GET `/tts?text=...&voice=...`, **not `/api/tts`**:
production forwards `/api/*` to Goose. `server/routes/tts.get.ts` limits `text`
to 200 JavaScript UTF-16 code units, not 200 UTF-8 bytes. Split longer narration
at sentence boundaries and measure the resulting audio. Never copy server TTS
keys into scene HTML. An unavailable audio service is not a successful voiceover.

Do not invoke Swan's `video:hsk:*` package commands: they reference
`scripts/hyperframes-hsk-short.mjs`, which was absent at inspection time.

## Refresh this contract against source

Inspect sibling checkouts `../goose` and `../swan` before assuming these contracts
have changed. Swan sources: `api/{word,grammar,articles,user,program}.ts`,
`composables/{httpConfig,useLanguagePreference,useHskColors,useWordVideoGenerator}`,
the corresponding `pages/` files, `utils/{grammarTitles,universityGallery}.ts`,
`plugins/tool.ts`, `nuxt.config.ts`, and `server/routes/tts.get.ts`.
Consult Goose detail handlers and response structs to confirm wire fields and
public visibility. `api/types.ts` is useful context, but some interfaces lag the
actual detail pages. Keep all project inspection read-only for video generation.
