# Assessed learning missions

Use this route when learning and quizzes are the product: textbook adaptations,
communicative errands, dialogue practice, and lesson-bound games. The existing
3D story scaffold remains available when the scene benefits from it.

## Start with a lesson

Use the sibling `mandarinai-lesson` skill to produce a validated package with stable
objective, item, question, and dialogue IDs. Read its lesson contract before writing
an adapter. Choose one observable outcome and one small situation. A food-ordering
mission can require choosing food, forming an order, and asking its price; movement
or pickups alone do not demonstrate those skills.

Keep the same question ID and content version in the lesson, game, and review log.
Re-presenting a revealed answer can advance the story, but it is assisted practice.
Use new prompts for an exit check and delayed variants for later review. Speech
recognition supplies transcript evidence; it does not certify tones or pronunciation.

## Match mechanics to the decision

| Objective | Useful mechanic | Evidence |
| --- | --- | --- |
| Understand a request | Choose an item after hearing or reading an NPC | Committed choice, assistance shown, prompt modality |
| Form an order | Arrange phrase chunks or type a constrained reply | Ordered IDs or accepted text variant |
| Ask for missing information | Information-gap dialogue choice | Reply asks the needed question in the new situation |
| Interpret a price | Pay the amount from the NPC line | Amount choice, with transcript exposure recorded for listening |
| Repair an exchange | Select a correction and try another example | Original mistake, correction viewed, new independent attempt |

Keep an untimed path, keyboard and touch controls, optional pinyin/translation, and
text feedback. Show game rewards separately from learning status. Replayed audio
can remain available; transcript/translation exposure must be recorded when judging
listening evidence. Judge the language answer independently of navigation speed.

## Swan integration

Inspect the current checkout before changing a contract. The reference baseline is:

- `utils/games.ts` and `pages/learn/activities/[type].vue` own registration and hosting.
  Keep `game-score`, `game-complete`, `game-exit`, and `game-restart` unchanged.
- `sessionMode` defines the one session owner. A game cannot complete a parent-owned
  session. Use shared GameResults, useGameTimer, tween, and audio lifecycle helpers.
- `utils/breakfastStreet.ts` already has authored steps, accepted text variants,
  scaffolds, deterministic state transitions, and device-local save/review exports.
  Reuse its scene and interaction design; its current records are not account SRS.
- `api/sessions.ts` currently selects by HSK/game/focus, with no lesson/question scope.
  Adding a query parameter or TypeScript field alone does not restrict Goose content.

Proposed scope, requiring an implemented backend or explicit local adapter:

```json
{
  "lessonId": "breakfast-order-01",
  "contentVersion": "1.0.0",
  "objectiveIds": ["order-food", "ask-price"],
  "questionIds": ["order-01", "price-01"],
  "seed": 42
}
```

Resolve canonical word/grammar IDs through Goose; never treat an authoring string ID
as an existing database integer. The service should validate scope and freeze a
versioned challenge plan, grade canonical answers, and deduplicate attempt IDs.
Unknown scope or unavailable content must give an explicit error. An authored local
prototype must label its device-only persistence and award no account XP. Never fall
back silently to unrelated HSK challenges or use client verdicts as authoritative XP.

Tutorial result aggregation also needs verification across every exercise kind before
using its percentage as mastery. Persist per-question evidence through a dedicated
adapter; keep scoring and assessment additions out of the fixed game event payload
unless that public contract is deliberately revised end to end.

## Verification adapted from Guizang

Retain the useful sequence: small playable slice, inspectable state, coherent assets,
actual play/audio review, and delivery checks. Add learning checks before art polish:

1. Validate IDs, answers, accepted variants, distractor feedback, and objective coverage.
2. Run correct, wrong, hint, reveal/retry, skip, restart, and completion scenarios.
3. Assert numeric progress and evidence as well as screenshots. Use deterministic
   fixtures isolated from real Goose submissions, XP, and personal-best storage.
4. Check a narrow mobile viewport, keyboard, IME, reduced motion, pause/visibility,
   reload, audio failure, and WebGL fallback when the scene uses it.
5. Listen to Mandarin separately from muted automation. Report language review,
   gameplay, machine validation, and unverified claims distinctly.

Generate new assets only when needed. Record provider/job IDs, status, content
version, usage rights, and cost so retries resume an existing job. Respect the
existing skill's AGPL attribution; upstream demo media is separately restricted.

For promotion, pass reviewed content and question references to `mandarinai-video`:
hook, worked exchange, retrieval hold, reveal, then a verified mission link. A recording
of a mocked local preview must be presented as a prototype, not a live Swan feature.
