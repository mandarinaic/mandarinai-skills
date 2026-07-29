---
name: mandarinai-flashcard
description: "Generate HSK / Mandarin vocabulary flashcards from live MandarinAi (mandarinai.com) dictionary data — 11k+ words, HSK 1-7/9, multilingual meanings, examples with translations; offline bundle as fallback. Every card links back to the word's mandarinai.com page. Outputs: Anki deck (.apkg, recognition + recall cards, optional TTS audio) and 1080x1440 PNG vocab cards. Input: an HSK level (e.g. 'HSK 3 下一组 20 个词'), an explicit word list, or a Chinese text passage to mine words from. Use when user says '闪卡', 'flashcard', 'Anki', '生词卡', 'HSK 卡片', '背单词', 'vocab cards', or asks to make study cards for Chinese words. NOT FOR 诗词/注音卡 (use mandarinai-card's -p mold) or 学习视频 (use mandarinai-story-video)."
user_invocable: true
version: "0.1.0"
---

# mandarinai-flashcard

把 HSK 词汇做成可以背的卡：Anki 卡组（.apkg）或 PNG 单词卡。

**数据以 mandarinai.com 实时 API 为准**（站点数据持续优化），离线 bundle 只是网络不可用时的兜底。每张卡都带回链到该词的 MandarinAi 详情页——卡组既是学习工具，也是网站的入口。

## 工作流

### Step 1 · 确定词集

三种输入：

1. **HSK 级别**：「HSK 3 的 20 个词」→ `--level 3 --count 20`；「下一组」用 `--offset` 翻页
2. **词表**：用户给出的词（逗号分隔或文件）→ `--words 爱,朋友` / `--words-file list.txt`
3. **文章挖词**：用户给一段中文 → 先分词，把词逐个对照 bundle（用 `--words` 批量传入，脚本会报告哪些不在词库），按级别分组后跟用户确认词集

bundle 不含的词会被跳过并警告——告诉用户哪些词没进卡组，不要静默吞掉。

### Step 2 · 选输出

**Anki 卡组**（默认）：

```bash
cd <SKILL_ROOT>
.venv/bin/python scripts/build-anki.py --level 3 --count 20 --audio \
  --deck-name "HSK 3 · 第一组" --out ~/Downloads/hsk3-01.apkg
```

- 每词两张卡：Recognition（认字 → 义）+ Recall（义 → 字），卡背带 "More on MandarinAi →" 回链
- `--language fr` 等可换释义/例句翻译语言（实时 API 支持多语；bundle 仅英文）
- `--audio` 嵌入发音 mp3（优先词条自带 audio URL，否则 TTS 兜底）
- `--source api` 强制实时数据（默认 auto：API 不可达才退 bundle 并警告）
- deck/model ID 确定性生成：同名卡组重复导入是**更新**不是重复

**PNG 单词卡**（小红书 / 分享用，1080x1440）：

```bash
.venv/bin/python scripts/build-anki.py --level 3 --count 9 --dump-json > /tmp/dump.json
python3 scripts/build-card.py /tmp/dump.json --word 爱 --png ~/Downloads/爱.png   # 每词一次
```

- 词典数据从 dump 原样进卡，不要手工转抄字段——品牌色阶、例句 ≤2 条、超长释义截到第一义项，都由 `build-card.py` 处理
- 同词多义条目脚本会警告并取第一条；要别的义项，把该词条单独存成 JSON（加 `"type": "vocab"`，结构见 `examples/vocab-ai.json`）再传入

**诗词／逐句注音卡**不在本 skill：交给 **mandarinai-card 的 `-p` 模具**（和紙暗框模板、
字号档位表、`scripts/validate-pinyin.py` 校验器都在那边）。用户要「诗词卡」「注音卡」
「古诗拼音」时直接转过去，别在这里另起一套。

### Step 3 · 验证

- Anki：`unzip -l <deck>.apkg` 看 media 数量；报告 note/card 数（脚本输出）
- PNG 单词卡：字段完整性与占位符由 `build-card.py` 校验，报错就改 JSON 数据；打开 PNG 只看视觉——大字没溢出、内容没贴到 footer
- 交付时报告：词数、跳过的词、文件路径

## 依赖（一次性）

```bash
cd <SKILL_ROOT>
python3 -m venv .venv && .venv/bin/pip install genanki   # Anki 打包
npm install                                              # PNG 渲染（playwright）
```

## 数据源

1. **实时 API（默认）**：`GET {MANDARIN_API_BASE}/api/flashcards/hsk?level=&page=&page_size=&language=` 或 `?words=爱,朋友`，返回卡片完整数据（goose `feat/flashcard-api` 分支，部署后即在 https://www.mandarinai.com 生效）。`MANDARIN_API_BASE` 默认 `https://www.mandarinai.com`，本地开发可指 `http://localhost:40002`。注意：站点 nginx 拦默认 curl UA，脚本已带浏览器 UA。
2. **离线 bundle 兜底**：`assets/hsk-cards-v1.json.gz`（11k+ 词，仅英文）。API 不可达时自动启用并警告"数据可能过期"。词库 enrich 后重导出：`python3 scripts/export-bundle.py`（需 docker 容器 pgvector-dev）。

## 运行环境适配

- Claude Code / Codex / Gemini CLI 全部走 shell 脚本，无平台专用依赖
- 生成的卡放 `~/Downloads/` 或用户指定位置，不要写进 skill 目录

## 约束

- 词义、例句、拼音一律以数据源（API / bundle）为准，不要自己编——这是词典数据，错一个字误导一个学生
- TTS 失败不阻断：缺音频照样出卡，告知用户哪些词没音频
- 不覆盖已有输出：`build-card.py` 遇到同名文件会拒绝，换个名字；确认要覆盖才用 `--force`
