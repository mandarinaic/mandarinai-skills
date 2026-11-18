# Learning layer

MandarinAi games teach while they tell the story. The layer is on by default and should
feel like part of the game, never a quiz bolted on.

## Dialogue lines

Every spoken line in `story.js` is `{ who, zh, py, en }`:

- `zh` — the line in simplified Chinese at the agreed level (HSK band). Plain modern
  Chinese; one famous classical phrase per game is fine if glossed.
- `py` — one syllable per hanzi, space-separated, no punctuation. The dialogue box renders
  one `<ruby>` per hanzi with the syllable above; punctuation stays outside the ruby.
  `dialogue.js` **throws** when counts differ and records the line in `G.errors`, so
  play-check fails until it is fixed.
- `en` — the translation (or the language the user chose), natural not word-for-word.

Pinyin rules (same as `../mandarinai-card/references/pinyin-annotation.md`, which has the
full 多音字 checklist):

- all lowercase, even names and sentence starts (lǐ bái, not Lǐ Bái)
- tone marks, never numbers; ü never v; neutral tone unmarked (de, le, ma, ba)
- 一 and 不 as pronounced (bú huì, yí gè); third-tone sandhi is NOT rewritten (nǐ hǎo)
- check every 多音字 in context: 还 hái/huán, 行 xíng/háng, 长 cháng/zhǎng, 得 dé/de/děi,
  地 dì/de, 重 zhòng/chóng, 只 zhī/zhǐ, 了 le/liǎo, 着 zhe/zháo, 为 wèi/wéi

Players toggle pinyin (P) and translation (T); both start on. For HSK 4+ you may start
pinyin off.

## Level control

- Agree the band in Step 0 (default HSK 2–3). Keep lines short: 6–14 hanzi.
- Reuse the story's key words several times; a word met once is not learned.
- New words above the band are fine if they are the story's own key words (河, 渡, 妖);
  they go in the collectible list.
- For a full graded text of the same story (a reader to accompany the game), use
  `mandarinai-reader`; for a deck of the collected words, `mandarinai-flashcard`.

## Collectible words

`story.words`: 3–8 entries `{ zh, py, en, at: [x, z] }`, chosen from the story's vocabulary
(the words the dialogue uses). Pickup shows a card (hanzi, pinyin, meaning) for ~2 s and
adds the hanzi to the HUD bag; the end screen lists them all. Words should gate progress
lightly (the gate needs all three) so players actually read them.

Optional extensions when the form allows (agree with the user first):

- **Read-to-act**: a choice between two lines in Chinese where the right reading advances the
  plot (trick/wit stories).
- **Tone gates**: pick the right tone of a syllable to open a door; keep it rare.
- **Audio**: voiced lines (see `assets.md` → Voice). The Swan TTS service used by the video
  skills can produce clean Mandarin per line; voice only the hero and the story's key lines.

## End screen

Title, result, the collected words as cards (hanzi / pinyin / meaning), the MandarinAi logo,
"Learn Chinese the Smart Way · mandarinai.com". No outbound links in a single-file build
unless the user asks.
