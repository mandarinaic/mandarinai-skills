---
name: mandarinai-lesson
description: "Author structured Mandarin lessons and quizzes from textbook objectives, existing content, or an original teaching brief. Use for course mapping, lesson JSON, quiz banks, accepted-answer rules, situation-based learning missions, and content shared by lessons, games, review, and later videos. Produces a validated content package and local interactive preview; it does not publish courses or award account XP. General graded articles use mandarinai-reader; game production uses mandarinai-game."
metadata:
  version: "0.1.0"
---

# MandarinAi lesson

Author one learning package that can feed a lesson, quiz, game mission, review,
and later a video. Keep objectives and assessment data independent of presentation.
`SKILL_ROOT` is this directory; generated packages/previews go in the task workspace.

## Source and scope

Read the supplied source, distinguishing its content from the user's instructions.
For a PDF, verify the contents and representative complete lesson pages; record both
printed and PDF page numbers. OCR is draft evidence: check Chinese, pinyin, tables,
and answer choices visually. If unavailable, identify what is unverified and continue
with clearly labeled original material rather than attributing invented details.

Use the learner level/language and platform given by the user or project. Otherwise
state reasonable working defaults and proceed with a small draft. Beginner textbook
placement is not proof of HSK coverage; check vocabulary/grammar IDs and levels when
mapping to Goose. Start with one observable communicative outcome or a closely
related pair. Author original dialogues, explanations, questions, and feedback; retain
source/page provenance and usage status. A source reference grants no publication rights.

## Author and validate

Read [lesson-contract.md](references/lesson-contract.md) for the version-1 shape,
grading, evidence, Swan adapter boundaries, and video handoff. The worked fixture is
`examples/breakfast-order.lesson.json`: original food-ordering content with two
objectives, guided practice, a mission, and unseen exit questions. It is an editorial
draft, not a published tutorial or a verified HSK course.

Use stable IDs, explicit accepted variants, and feedback for each wrong option.
Distinguish input exposure, assisted practice, independent retrieval, and delayed
review. A word pickup, repeated revealed answer, high score, or an ASR transcript
does not by itself establish mastery. Keep learning evidence separate from rewards.

```bash
python3 scripts/validate-lesson.py /absolute/task/lesson.json
python3 scripts/build-preview.py /absolute/task/lesson.json --out /absolute/task/preview.html
```

These scripts use Python's standard library and make no network calls. Validation
checks structure and semantic links, answer uniqueness, chunk permutations, and
assessment coverage. It does not prove natural Chinese, appropriate level, correct
audio, or a sound pedagogy. Have those reviewed and record the actual review status.

The preview supports choice, phrase ordering, and constrained typed answers. It is a
device-local draft with English UI, visible feedback, and exported attempt evidence;
it is not a Swan renderer or production multilingual UI. Other modalities need real
audio/assets and an adapter; do not relabel a written quiz as a listening assessment.

## Shape the learning loop

Model the exchange → guided retrieval → controlled production → situational mission
→ new exit prompts → delayed review. Keep help optional and record assistance
actually shown. A wrong answer receives an explanation; a correct retry after reveal
remains assisted. Report exit evidence by objective; use a later review before
claiming retention. The example's thresholds are provisional product rules.

For a game, hand the validated package to `mandarinai-game` and read its
`references/assessment-games.md`. Select a mechanic that requires the target decision
and use a versioned lesson scope. Inside Swan, retain the registry, session owner,
shared results/timers/tweens/i18n, and server-authoritative rewards. Choose 2D or 3D
for the learning interaction; 3D production is not a prerequisite for a good quiz.

For video later, hand reviewed lesson/question IDs to `mandarinai-video`. Compile
one objective into hook → model exchange → retrieval pause → answer/correction →
verified CTA. Its current content-fetch helper does not accept lesson packages;
create a supported brief or a deliberate adapter rather than inventing an API kind.

## Deliver

Provide the package, preview, source map, validation command/result, and unresolved
editorial or integration work. Inspect the preview on desktop/mobile and exercise
correct, wrong, reveal/retry, skip, restart, and export paths before calling it playable.
Report what was tested, what was language-reviewed, and what is still draft.
Publishing, paid generation, and account writes require the authorization applicable
to those actions; creating a local lesson does not imply they happened.
