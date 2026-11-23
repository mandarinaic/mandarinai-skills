# Lesson package v1

This is an authoring contract, not the existing Goose API wire format. See
`examples/breakfast-order.lesson.json` for a complete package and the validator for
supported fields. The IDs are authoring keys; database mappings are resolved later.

## Shape

| Field | Meaning |
| --- | --- |
| `schema_version`, `id`, `version`, `course_id` | Schema and stable content identity; bump content version when answers or instructional meaning change |
| `title`, `level`, `editorial` | Localized title, descriptive placement and review status; no unsupported HSK claims |
| `sources[]` | ID, title, role (`topic-reference` or `original`), verification/rights notes and optional printed/PDF pages |
| `objectives[]` | ID, learner can-do text, evidence policy |
| `vocabulary[]` | ID, Chinese, word pinyin, translation; optional future Goose ID mapping |
| `patterns[]` | ID, pattern, explanation and reviewed original example |
| `dialogue[]` | Stable turn ID, speaker, Chinese, natural pinyin, translations; this is model input |
| `questions[]` | Objective-linked question, answer rule, rationale, support and purpose |
| `flow[]` | Ordered activities: `practice`, `mission`, `exit`, with exact question IDs |
| `review` | Delayed-review policy and evidence scope |

Chinese/pinyin/answers/IDs stay fixed across translation overlays. Translate prompts,
feedback, explanations and UI independently. Word-level pinyin is not automatically
per-Hanzi ruby; use an aligned syllable list only where a renderer needs one.

## Supported question contract

Every question has `id`, `objective_ids`, `vocabulary_ids`, `pattern_ids`, `source_ids`,
`phase`, `skill`, `type`, `prompt`, `hint`, `feedback`, `difficulty`, and `answer`.
Prompts, hints, and feedback are locale maps (the draft requires English).

- `phase`: `practice`, `mission`, or `exit`; every question appears in exactly one
  flow step and must agree with the step's phase.
- `skill`: `meaning`, `comprehension`, `word-order`, `production`, or `interaction`.
- `choice`: options `{id, text, feedback}` plus `answer.option_id`. Each wrong option
  needs feedback addressing its misconception. Use stable option IDs for grading;
  shuffling changes display order only. One answer is correct for the stated task.
- `order`: chunks `{id, text}` plus `answer.chunk_ids`. The answer must contain each
  ID exactly once. The preview presents an unsolved order and preserves repeated
  words as separate chunk IDs.
- `text`: `answer.accepted[]` plus `answer.normalization`. Default explicit policy:
  NFKC compatibility forms, whitespace and a declared punctuation list are ignored.
  Do not strip arbitrary symbols, fold characters/synonyms, or remove diacritics.
  Accepted variants must be distinct under that policy. Free conversation needs a
  separate rubric, not an exact string test with one canonical sentence.
- `feedback.correct` explains the decision; `feedback.incorrect` corrects it.
- `difficulty`: descriptive integer 1–5, not an automatically verified learner level.

Exit questions have new prompts/answers not shown as guided items or in the model
dialogue. The validator catches repeated prompts; editorial review must catch semantic
leakage. Closed-choice exit success demonstrates constrained comprehension/interaction,
not free speech. The fixture has no scored audio; scripts for later TTS are not audio.

## Evidence and review

Attempt identity: `attempt_id`, `run_id`, `lesson_id`, `content_version`, `question_id`,
`objective_ids`, `attempt_number`, `response`, `correct`, `hint_used`, `revealed`,
`skipped`, `latency_ms`, `phase`, and `recorded_at`. Keep attempts immutable.

For the preview, independent evidence is a correct first submission without a hint
or reveal on that question. A wrong first submission followed by a correction/retry
cannot become independent evidence. Skips have `correct: null`, never a hidden zero
or success. Input and answer events are separate; navigation awards no learning credit.

The fixture requires both a comprehension and a production/interaction success in the
exit phase for each objective. Call that status “exit demonstrated.” Retention remains
pending until a delayed independent check with different prompts. An account service
would validate attempts and schedule review; the prototype only exports local evidence.
Do not interpret its local records as signed server events or account XP.

Content version and account ID must partition production evidence. Backend writes
need idempotency, exact-operation retry, stale/account response protection, and
server-owned verdicts/rewards. These are integration work, not existing preview features.

## Swan adapters

1. Map package course/unit/lesson IDs to Goose tutorial IDs. Map canonical vocabulary
   and grammar records separately; do not fabricate numeric content IDs.
2. Render the model and exercises through `api/tutorial.ts` lesson block types.
   Existing translation overlays preserve taught Chinese/pinyin and answer structure.
3. Normalize item-level result events across tutorial child components. Some current
   exercise types are omitted from the lesson's first-attempt block aggregate.
4. For games, validate `{lessonId, contentVersion, objectiveIds, questionIds, seed}`
   and freeze a server challenge plan. Current HSK-only sessions cannot promise this.
   A device-local authored adapter is acceptable if its limits are explicit.
5. Retain fixed game events, one session owner, shared GameResults/timer/tween and
   six-locale UI. Send objective evidence via a distinct supported contract.

`utils/breakfastStreet.ts` is the closest authored interaction precedent. Its local
encounters, successes, struggles and review export need an explicit bridge to account
SRS; a local word encounter must not be sent as an independently recalled word.

## Later video handoff

Take a reviewed snapshot; preserve lesson/content version, objective and question IDs.
Select one supported brief format in `mandarinai-video`: hook, original model exchange,
recall hold, reveal, correction and CTA. Hide answer text from the recall scene until
the reveal cue. Timing follows measured audio plus reading time; music sits below speech.
Record asset provider/job/status/license/cost/checksum and reuse finished jobs on retry.
Export captions and both 9:16 and 16:9 when requested. Validate a real mission URL
before using it; a local preview has no published course ID or live mission claim.
