# Story → game adaptation

## Rights first

| Source | What you may do |
|---|---|
| Pre-modern classics and folk tales (西游记, 三国演义, 水浒传, 聊斋志异, 史记, 庄子, 寓言, 成语故事, 十二生肖, 嫦娥, 后羿, 女娲, 精卫, 愚公移山…) | Adapt freely. Quote the original text. Name the source on the title screen ("改编自《西游记》第二十七回"). |
| Modern translations or retellings of a classic | The underlying story is free; the translator's wording is not. Write your own lines. |
| Modern copyrighted books, films, games, comics (incl. TV adaptations of classics) | Original game *inspired by* the theme only: no quoted text, no character names or designs, no recognisable scenes or art direction. Say so to the user. |
| The user's own book or story | Ask them to confirm they hold the rights; then adapt freely. |

Never recreate an existing game (its name, levels, characters, look) even when the story
is public domain: 西游记 is free, a specific commercial 西游 game is not.

## From text to beats

1. Read the actual text (the chapter, not a summary). For a whole book, run
   `mandarinai-book` first and pick one episode: one game = one episode.
2. Write 5–8 beats: setup → want → obstacle → turn → climax → resolution. Each beat is one
   playable moment or one short scripted moment, never a wall of text.
3. Pull 2–4 lines of real dialogue per key beat (classical → plain modern Chinese at the
   chosen level; keep one famous line verbatim if the level allows, e.g. 俺老孙来也).
4. Find the **core verb** of the story: travel, race, fight, trick, build, rescue, search,
   choose. The game form follows the verb, not the setting.
5. Keep the moral but do not lecture: show it in the ending beat, one line.

## Form table

| Core verb | Form | Typical scope | Example stories |
|---|---|---|---|
| race, contest | timed run with an obstacle and a helper | 1 scene, 3–5 min | 十二生肖, 龟兔 style contests, 田忌赛马 (choice-based) |
| journey, search | exploration with NPCs and collectibles | 1–2 scenes | 精卫填海, 嫦娥奔月, 桃花源记 |
| fight, defeat | top-down action, a small fight, one boss | 1 scene + boss arena | 三打白骨精, 武松打虎 (tiger as generated beast, not Kai), 哪吒闹海 |
| trick, wit | dialogue choices or a logic puzzle | 1 scene, branching lines | 草船借箭, 空城计, 曹冲称象 (weigh-the-elephant puzzle) |
| build, persist | gather-and-build loop | 1 scene | 愚公移山, 铁杵磨成针, 大禹治水 |
| idiom / fable | 2–4 minute micro-game teaching one idiom | 1 small scene | 守株待兔, 刻舟求剑, 画蛇添足, 井底之蛙, 揠苗助长 |

Scope rule from experience: **one scene, one encounter, one finale**. A second scene is
earned only after the first is polished. 3–10 minutes of play is plenty.

## Casting stories with the MandarinAi cast

Cast a MandarinAi character only when the role matches species, temperament, and age —
the brand gains from a good fit and loses from a forced one. Full roster and per-character
notes: `cast-3d.md`. Good fits:

- **十二生肖** — the whole zodiac cast plays itself (the starter game).
- **西游记** — Xiang (monkey) as the 孙悟空 figure, Xin (pig) for 猪八戒-style comic warmth
  (keep him lovable, not a glutton joke), Wei (dragon) as 小白龙; 唐僧 and 沙僧 are generated.
- **嫦娥奔月** — Lina (rabbit) as 玉兔.
- **曹冲称象** — Maya or Bai as the clever child-solver stand-in only if the user wants a
  modern frame; otherwise generate 曹冲.
- **愚公移山 / 铁杵磨成针** — Bo (ox) for persistence; Jin as the wise elder who answers.
- **Framing device** — Yue or Jin as a storyteller who opens and closes the game, while the
  story itself uses generated characters. Use this when nothing fits a story role.

Never cast a MandarinAi character as a villain, a monster, a victim of violence, or a fool.
Antagonists (白骨精, the tiger in 武松打虎, 东海龙王's soldiers) are generated.

## Scale and tone

- Learners are the audience. Violence is stylised: enemies dissolve into ink or light,
  nobody bleeds, nothing is gory. Bosses can be menacing; the cast cannot.
- Text on screen is short. One line of goal at the start, two or three lines per character
  per beat, one closing line. No exclamation-heavy narration, no "PHASE TWO" banners.
- Titles: Chinese title + English subtitle + "改编自《…》" source line.
