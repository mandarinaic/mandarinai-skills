---
name: mandarinai-illustration
description: Generate house-style material illustrations, labeled explanatory visuals, material-styled chart illustrations, and data-first editorial images from articles, notes, product concepts, workplace reports, creator posts, tutorials, school materials, humanities topics, science explanations, screenshots, or chart data. Use when the user asks for 配图, 带字插图, 解释图, 图解插画, 概念拆解图, 图表美化, 数据图美化, 3D 图表, 汇报配图, 内容配图, 小学课文配图, 生物/化学/物理解释图, 人文类配图, process/loop/system diagrams, or wants GPT-Image / image generation to create supporting images that can sit inside social cards, docs, slides, PPTs, or posts.
version: "1.0.0"
---

# MandarinAi Material Illustration

<!-- attribution: mandarinai-illustration is derived from guizang-material-illustration by 歸藏 (https://github.com/op7418/guizang-material-illustration), AGPL-3.0, see LICENSE. Keep this notice in the skill; never write it into generated images or prompts. -->

## MandarinAi 品牌基调（署名/点缀用）

- 品牌名写法固定：**MandarinAi**（中文语境可用 **MandarinAi中文学习网**）；官网 mandarinai.com；tagline：**Learn Chinese the Smart Way**
- 品牌色：主色蓝 `#1b46a2`、点缀黄 `#ffc107`；HSK 等级色：HSK1 `#ffc107` / HSK2 `#17707F` / HSK3 `#B45309` / HSK4 `#B71A27` / HSK5 `#303255` / HSK6 `#4A1C57` / HSK7-9 `#1E7E34`
- 品牌字体：Noto Sans SC（正文）/ Noto Serif SC（装饰标题）/ JetBrains Mono（代码/数据）
- 官方 logo：横版字标 `mandarinai-illustration/assets/brand/mandarinai-logo.png`（2600×1000 透明底）、方形 icon `mandarinai-illustration/assets/brand/mandarinai-icon.png`（1000×1000 透明底）；卡片署名头像用 `mandarinai-card/assets/logo.png`（460×460 白底圆裁安全版）
- **用法**：品牌元素只用于署名、页脚、封面落款等 accent 位置，不覆盖各模式/主题自身的配色系统；仅当用户明确要"品牌风/官方风"时才整体采用品牌色

Create supporting illustrations from source text, screenshots, or chart data. The output is an image-generation prompt plan plus generated raster images when image generation is available.

This skill focuses on the illustration layer, not the full social-card layout. If the user also needs Xiaohongshu/WeChat card composition, pair this skill with mandarinai-social-card: use this skill for the central illustrations, then place the generated images in the card template.

This skill does not replace mandarinai-ppt or the mandarinai-social-card text-layout skill. Use those skills for slide structure and 3:4 text/card layout. Use this skill for the visual asset that goes into those layouts.

## Workflow

1. Read the user's source text, screenshot, or data and identify the concepts or charts that deserve supporting images.
2. Decide the working mode yourself from context. Do not ask the user to choose a mode unless the missing choice would materially change the result. If clarification is needed, ask naturally in one short sentence and offer a recommended default.
3. If the source is a chart screenshot, extract only chart type, title, data, axis labels, axis range, tick labels, units, category order, and error bars. Do not carry over screenshot colors, typography, spacing, shadows, or background.
4. If the concept, entity, object, historical/cultural context, scientific mechanism, species, material, brand, model, or place is likely unfamiliar or visually specific, look up reference information and/or reference images before prompting. Use references to understand and extract stable visual cues, then translate those cues into the house visual system.
5. Compress each non-chart concept into one plain-language explanation and 3-5 visible diagram labels when labels help. Some editorial or humanities illustrations may need fewer labels.
6. Choose a visual structure for each concept:
   - Cycle: repeated work, feedback, loops, iteration.
   - Pipeline: ordered steps, routing, transformation, workflow.
   - Hub-and-spoke: one center coordinating several branches.
   - Before/after: state change, upgrade, migration, comparison.
   - Layer stack: architecture, hierarchy, dependencies.
   - Data-first scene: chart or metric panel embedded in a topical scene.
   - Scientific mechanism: object, parts, forces, reactions, or biological process.
   - Text scene: a literary, historical, or everyday scene that anchors an abstract idea.
7. Write one image prompt per illustration. Make the prompt describe exact label text or chart data, aspect ratio, safe margins, references used, and shared house visual style.
8. Generate the images. Preference order: (a) the bundled `scripts/generate-image.mjs` when `OPENAI_API_KEY` or `GEMINI_API_KEY` is set (see Generating Images below); (b) a built-in image tool or image-generation MCP available in the current agent environment. If neither exists, say so, deliver the finished prompt plan in `PROMPTS.md`, and tell the user to paste each prompt into their image tool (GPT-Image, Gemini, Midjourney, etc.) — do not silently skip generation.
9. Inspect each image. If labels are wrong, chart data is wrong, reference cues are misleading, unreadable, or clipped, regenerate with stricter constraints.
10. Save prompts and final image paths in the task folder so the image set can be reproduced.

## Text Rules

- Use everyday Chinese. Avoid literal field labels like `Trigger`, `Stop`, `Use` unless the user explicitly wants bilingual UI.
- Keep labels short: 2-5 Chinese characters is ideal; 6 characters is usually the upper limit.
- Put explanatory sentences outside the illustration when the final artifact has a surrounding layout. Inside the illustration, only label objects and flows.
- Prefer concrete labels over abstract nouns. Use `用户提示`, `AI 执行`, `结果检查`, `下一轮`; not `输入阶段`, `执行阶段`, `验证阶段`.
- If the model struggles with Chinese text, shorten labels further and use distinct positions: top-left, top-center, top-right, bottom-center.
- Do not add a dense legend inside the image. If a viewer needs a paragraph, it belongs in HTML/CSS, Markdown, or slide text.

## Visual System

Read `references/visual-style.md` before generating a new set. It defines the default 3D Swiss editorial style, aspect ratios, safe-area rules, and supported accent colors.

Read `references/prompt-patterns.md` when drafting prompts. It contains reusable prompt shells for cycle, pipeline, hub, before/after, and layer-stack diagrams.

Read `references/chart-beautify.md` when the input is a chart screenshot, table, metric list, benchmark result, or the user asks to beautify a chart. It covers how to preserve exact values while giving the chart the same material illustration style.

Read `references/use-cases-and-routing.md` when deciding what kind of image to create from vague user input, education materials, humanities topics, or mixed article/data sources.

Read `references/reference-gathering.md` when the topic contains unfamiliar concepts, specific entities, scientific objects, cultural artifacts, historical scenes, brand/model names, or anything where visual accuracy matters.

Read `references/characters.md` when the content calls for a MandarinAi mascot, narrator, or recurring IP figure (WeChat 配图, social-card characters, PPT section mascots, zodiac/seasonal content). It catalogs the 19-character brand universe (12 zodiac companions + 7 human learners/mentors), the casting guide, and the `--ref` workflow that keeps generated characters on-model against the sheets in `assets/characters/`.

Read `references/qa-checklist.md` before delivering final images.

## Generating Images

The bundled script calls the OpenAI or Gemini image API directly — no SDK, Node 18+ only:

```bash
node <SKILL_ROOT>/scripts/generate-image.mjs --prompt-file <task-dir>/prompt-01.txt \
  --ratio 1.9:1 --out <task-dir>/assets --name agent-loop
```

- Credentials come from the environment: `OPENAI_API_KEY` (GPT-Image) and/or `GEMINI_API_KEY` (also accepts `GOOGLE_API_KEY`).
- Custom endpoints: set `OPENAI_BASE_URL` (default `https://api.openai.com/v1`) and `GEMINI_BASE_URL` (default `https://generativelanguage.googleapis.com`) to route through a proxy or compatible gateway.
- Models default to `gpt-image-1` / `gemini-2.5-flash-image`; override with `--model` or `OPENAI_IMAGE_MODEL` / `GEMINI_IMAGE_MODEL`.
- `--provider auto` (default) tries OpenAI first (stronger Chinese-label rendering), then Gemini; `--provider openai|gemini` pins one.
- `--ref <image>` (repeatable) supplies reference images for character/style consistency — required when drawing the MandarinAi characters (see `references/characters.md`). OpenAI routes through `images/edits`; Gemini passes the images inline.
- Prefer `--prompt-file` over `--prompt` — the prompt shells in `references/prompt-patterns.md` are multi-line.
- `--ratio` takes the ratios from `references/visual-style.md` (`1.9:1` default, `16:9`, `1:1`, …). OpenAI maps any ratio to its nearest fixed size (1536x1024 / 1024x1536 / 1024x1024), so expect to crop to the exact well; Gemini honors named ratios directly.
- The script auto-appends each image's provider, model, ratio, and full prompt to `<out>/PROMPTS.md`, which covers the record-keeping step.
- On failure it prints the API's error body — surface that to the user instead of retrying blindly (common causes: OpenAI org not verified for image models, quota, or a blocked prompt).

## File Handling

Create a task folder instead of writing loose assets next to this skill. Default to:

```text
local-tests/<slug>/
├── assets/
│   └── generated illustration images
└── PROMPTS.md
```

When pairing with another project, use that project's task folder if the user specifies one.

For each final image, record:

- Concept name.
- Final prompt.
- Output image path.
- Any rejected attempt and the reason if it matters for reuse.

## Quality Check

Before delivery, visually inspect each image and confirm:

- The whole diagram fits the requested image well; no important object or label is cropped.
- Chinese labels are legible and match the requested text.
- Label positions point to the right objects.
- Accent color is consistent across the set.
- The image contains no accidental logos, watermarks, UI chrome, or unrelated English text.
- The illustration can still be understood at social-card size.
