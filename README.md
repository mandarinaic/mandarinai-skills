# mandarinai-skills

**MandarinAi** agent skills — the toolchain behind mandarinai.com
("Learn Chinese the Smart Way"): the content side (articles, cards, decks,
illustrations, videos) and the learner side (HSK flashcards, graded readers,
narrated story videos, backed by the site's live dictionary data).
Usable from Claude Code, OpenAI Codex CLI, Gemini CLI, and Antigravity (`agy`).
All of these tools support the same [Agent Skills](https://agentskills.io) standard:
a skill is a directory containing a `SKILL.md` with `name` + `description` frontmatter,
plus optional `references/`, `scripts/`, and `assets/`.

Everything the skills emit is branded MandarinAi: signatures, brand blue `#1b46a2` /
accent yellow `#ffc107`, the 中文-badge logo, and the 19-character brand universe
(12 zodiac learning companions + 7 human learners/mentors — see
`skills/mandarinai-illustration/references/characters.md`).

## Skills

### Content creation

| Skill | What it does | Extra deps |
|-------|--------------|------------|
| `mandarinai-ppt` | Single-file HTML horizontal swipe decks (electronic-magazine or Swiss style), WebGL backgrounds, validated layouts | none |
| `mandarinai-social-card` | Xiaohongshu 3:4 card sets + WeChat 21:9 / 1:1 cover pairs in the same style system | Playwright (validation) |
| `mandarinai-illustration` | Labeled material illustrations (带字解释图), chart beautify, concept visuals, and **MandarinAi character images** (on-model via `--ref` against the character sheets) — the "middle image" inside cards/PPT/articles | `OPENAI_API_KEY` and/or `GEMINI_API_KEY` for bundled generate-image.mjs (custom endpoints via `OPENAI_BASE_URL` / `GEMINI_BASE_URL`); prompt plans work without any key |
| `mandarinai-card` | "铸" content caster — turns any content into PNG visuals (long card, infograph, sketchnote, comic, whiteboard, big-font card), signed MandarinAi | Node + Playwright |
| `mandarinai-paper` | Retells an academic paper as a seven-beat story for non-academics | none |
| `mandarinai-writes` | Writing engine — dissects one opinion into a 1000-1500 word essay | none |
| `mandarinai-wechat` | WeChat 公众号 writer — hook title (4-5 candidates) + scannable mobile layout + golden quotes + CTA ending; 配图 via the MandarinAi character universe; optional Chrome-CDP draft publishing (no API keys) | none to write; image API key for 配图, Playwright for publishing |
| `mandarinai-wechat-layout` | WeChat 公众号 layout engine — Markdown/docx/PDF → themed inline-styled HTML that pastes into the 公众号 editor without losing styles; 6 theme component libraries + theme generator, auto chapter numbering, keyword underlines, dual lint/validate scripts, copy-button preview page | python3 (validators) |
| `mandarinai-video-fetch` | Video link → clean transcript (YouTube / bilibili / xiaohongshu / douyin); feeds mandarinai-writes / card / ppt | yt-dlp + ffmpeg; whisper for no-sub videos |
| `mandarinai-book` | 拆书 — deconstructs a book (问题/零点/位移/落点/行囊) + ASCII cognitive map; grounds on web or local EPUB/PDF | none (pdftotext for PDFs outside Claude Code) |
| `mandarinai-video` | Promo/tutorial MP4s for Goose HSK words, grammar, universities, and processed articles; real Swan links, editable preview, measured narration, SRT, verified audio/video; standalone templates retained | Python 3 + Node + Playwright + ffmpeg |

### Mandarin learner tools

These are the ones that face students rather than readers. They chain:
**`mandarinai-reader`** writes the graded article → **`mandarinai-story-video`** narrates
it → **`mandarinai-flashcard`** turns its 生词表 into a deck. Poem/pinyin cards are
**not** here — they're the `-p` mold of `mandarinai-card`.

| Skill | What it does | Data source | Extra deps |
|-------|--------------|-------------|------------|
| `mandarinai-flashcard` | HSK / vocab flashcards: Anki `.apkg` (recognition + recall, optional TTS audio) and 1080x1440 PNG vocab cards, each linking back to the word's mandarinai.com page | live `mandarinai.com/api/flashcards/hsk` (11k+ words, HSK 1–7/9, multilingual); bundled export as offline fallback | python venv (genanki), Node + Playwright |
| `mandarinai-reader` | Turns a video (Rednote/Bilibili/YouTube/Douyin), article, or topic into an HSK-graded reading article — controlled vocab + grammar, optional 生词表 / pinyin / grammar points | pure text generation; pairs with `mandarinai-video-fetch` for transcripts | none |
| `mandarinai-story-video` | Graded-story 1080x1440 learner videos with ruby pinyin, approximate character reveal, translations, TTS, title/end cards; use `mandarinai-video` for promos and other tutorials | Swan `/tts`; real article sentences can come from the video source helper | Node (gsap + hyperframes), ffmpeg |

### Content-driven video production

`mandarinai-video` reads Goose content records and links back to Swan: words at
`/hsk/word/detail/{id}`, grammar at `/grammar/detail/{id}`, universities at
`/university/detail/{id}`, and processed articles at `/tools/articles/{id}`.
It also accepts saved detail exports. The workflow draws on
[huashu-motion](https://github.com/alchaincyf/huashu-motion) and
[huashu-art-motion](https://github.com/alchaincyf/huashu-art-motion), using this
repository's own renderer and MandarinAi assets.

From `skills/mandarinai-video/`, with real input paths and a new output directory:

```bash
python3 scripts/prepare-content.py --kind grammar --id REAL_ID --out /absolute/task/source.json
python3 scripts/build-project.py /absolute/task/brief.json --source /absolute/task/source.json --out /absolute/task/project --tts
python3 scripts/render-project.py /absolute/task/project --output /absolute/task/tutorial-v1.mp4
```

The agent authors the brief against the source; see
[`references/production.md`](skills/mandarinai-video/references/production.md)
and four example briefs. Narration uses local audio or Swan `/tts`; `--silent`
explicitly makes a silent draft. Captions are phrase-level SRT sidecars, not burned
subtitles. MP4 output includes verification and review frames. Samples are marked
synthetic and use real library URLs rather than invented published IDs.
Generation reads data and writes local artifacts; publishing and Goose/Swan
changes are separate tasks.

Video regression checks (no API calls):

```bash
python3 -m unittest discover -s skills/mandarinai-video/tests -v
# Optional local browser/FFmpeg integration checks, after installing video dependencies:
node --test skills/mandarinai-video/tests/browser-smoke.mjs
# Set MANDARIN_VIDEO_BROWSER=/path/to/chrome to use an installed browser.
```

### One-time dependencies

All five Playwright skills pin the same version (1.59.1), so the chromium
download is shared — it only actually downloads once. Run from the repo root:

```bash
# mandarinai-wechat is only needed for optional Chrome-CDP publishing (writing needs nothing)
for s in card social-card video wechat flashcard; do
  (cd "skills/mandarinai-$s" && npm install && npx playwright install chromium)
done

# mandarinai-story-video renders with hyperframes instead (downloads its own browser on first render)
(cd skills/mandarinai-story-video && npm install)

# mandarinai-flashcard also needs a venv for Anki packaging
(cd skills/mandarinai-flashcard && python3 -m venv .venv && .venv/bin/pip install genanki)

# ffmpeg: mandarinai-video and mandarinai-story-video
brew install ffmpeg
```

## Brand

- Name is always written **MandarinAi** (Chinese contexts: **MandarinAi中文学习网**); site `https://www.mandarinai.com`; tagline **Learn Chinese the Smart Way**.
- Brand blue `#1b46a2`, accent yellow `#ffc107`, HSK level palette, Noto Sans SC / Noto Serif SC — each visual skill carries a "MandarinAi 品牌基调" block in its SKILL.md.
- Official marks (transparent PNG): horizontal wordmark + square icon in `skills/mandarinai-illustration/assets/brand/`; `skills/mandarinai-card/assets/logo.png` is the circle-crop-safe avatar version used in card signatures.
- Character universe: model sheets in `skills/mandarinai-illustration/assets/characters/`, casting guide + generation workflow in `references/characters.md` of the same skill. 3D `.glb` versions of every character exist outside this repo.

## Credits & licensing

Several skills started as adaptations of upstream open-source work and have since been
rebranded and heavily modified for MandarinAi; attribution notices are kept in each
`SKILL.md`. Four skills remain **AGPL-3.0** per their upstream license (a `LICENSE`
copy sits inside each): `mandarinai-ppt`, `mandarinai-social-card`,
`mandarinai-illustration` (from 歸藏's guizang skills) and `mandarinai-wechat-layout`
(from gzh-design-skill by 甲木 × 摸鱼小李). `mandarinai-video` includes Apache-2.0
render-pipeline code from nexu-io/html-video (see its `LICENSE`). Its new project
workflow references Huashu's production methods without bundling their runtimes
or demo assets; source links and licensing context are in
`skills/mandarinai-video/references/motion-direction.md`. The remaining skills are MIT.

## Layout

```
mandarinai-skills/
├── skills/<skill>/         # one directory per skill
│   ├── SKILL.md            # required: frontmatter + workflow
│   ├── references/         # deep docs, loaded on demand (progressive disclosure)
│   ├── scripts/            # deterministic helpers (validators, converters)
│   ├── assets/             # templates the skill copies/fills in
│   └── agents/openai.yaml  # optional Codex UI metadata
├── skill-template/         # copy into skills/ to start a new skill (ships TEMPLATE.md, not SKILL.md, so installers skip it)
├── scripts/install.sh      # symlinks skills into all three CLIs
└── .claude-plugin/
    ├── plugin.json       # makes the repo installable as a Claude Code plugin
    └── marketplace.json  # makes the repo installable in Antigravity (agy) — lists all skills
```

## Install (local development)

```bash
./scripts/install.sh
```

This symlinks every skill into `~/.claude/skills/` (Claude Code) and
`~/.agents/skills/` (Codex CLI and Gemini CLI both scan this shared location).
Because they are symlinks, editing or pulling this repo updates all CLIs at once.

## Install (from GitHub, once published)

```bash
# all skills, into the three CLIs this repo targets
npx skills add mandarinaic/mandarinai-skills -g -s '*' -a claude-code -a codex -a gemini-cli -y

# one skill
npx skills add mandarinaic/mandarinai-skills -g -s mandarinai-card -a claude-code -a codex -a gemini-cli -y
```

Don't use `--all`: it expands to `--agent '*'` (every agent the CLI knows), and
agents that lack global-install support (e.g. PromptScript) abort the run with
"does not support global skill installation". Name agents explicitly with
repeated `-a` flags (comma-separated lists are not parsed).

## Install (Antigravity CLI `agy`)

`agy` doesn't scan `~/.claude/skills` or `~/.agents/skills`; it uses a plugin
marketplace. This repo ships `.claude-plugin/marketplace.json` (one plugin
exposing all skills), so inside an `agy` session:

```text
/plugin marketplace add mandarinaic/mandarinai-skills
/plugin install mandarinai-skills@mandarinai-skills
```

Or from a local clone, point `agy` at the repo root (it reads the marketplace
manifest and registers every skill):

```bash
agy plugin install ./        # run from the repo root
agy plugin list              # confirm: imports → mandarinai-skills, components: [skills]
```

## Creating a new skill

1. `cp -r skill-template skills/my-skill && mv skills/my-skill/TEMPLATE.md skills/my-skill/SKILL.md`
2. Edit `SKILL.md`: set `name: my-skill` (must match the directory), write the
   description with explicit trigger phrases — the description is the only thing
   the model sees before deciding to use the skill.
3. Delete unused folders; keep `SKILL.md` under ~500 lines, push detail to `references/`.
4. `./scripts/install.sh`, restart the CLI, test the trigger phrase in all three tools.

## Per-CLI notes

| CLI | Skill location | Trigger | Notes |
|-----|----------------|---------|-------|
| Claude Code | `~/.claude/skills/` | automatic, or `/my-skill` | also installable as plugin via `.claude-plugin/` |
| Codex CLI | `~/.agents/skills/` | automatic, or `$my-skill` / `/skills` | optional `agents/openai.yaml` for UI metadata |
| Gemini CLI | `~/.agents/skills/` (alias of `~/.gemini/skills/`) | automatic; `/skills list` to inspect | needs v0.26+; asks permission on activation |
| Antigravity (`agy`) | plugin store (not a skills dir) | automatic once installed | install via marketplace, not the symlinks — see "Install (Antigravity CLI)". `agy` resolves a plugin's skills from `marketplace.json`, so `.claude-plugin/marketplace.json` is required (a bare `plugin.json` is not enough) |
