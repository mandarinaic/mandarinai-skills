---
name: mandarinai-story-video
description: "把一篇分级中文故事（mandarinai-reader 的产出、用户给的句子，或一个话题）做成竖屏学习短视频（1080x1440 MP4）：每句一幕，汉字逐字 ruby 注音、跟读式逐字点亮、句末浮现译文，逐句 TTS 朗读，MandarinAi 片头片尾。Use when user asks to 把故事/文章做成视频, 做学习短视频, story video, 朗读视频, '做成抖音/小红书/Shorts 视频', or wants a vertical Mandarin learner video with pinyin and narration."
metadata:
  version: "0.2.0"
---

# mandarinai-story-video

把分级中文故事做成**竖屏学习短视频**：每句一幕，汉字带逐字小写拼音，跟着朗读逐字点亮，句子读完浮现译文；片头片尾带 MandarinAi 品牌。默认 1080×1440、30fps 的 MP4，30–60 秒。

上游搭配 mandarinai-reader（文章来源，分级标准也照它的 `references/leveling.md`）；生词可接 mandarinai-flashcard。结构规则全部由 `scripts/build-video.py` 负责——你只提供正确的句子、拼音、译文。

本 skill 专注逐句跟读。HSK 词汇讲解、语法公式、大学介绍、Swan 操作教程和宣传片用 `mandarinai-video`。已处理文章的实际内容可先用该 skill 的 `scripts/prepare-content.py --kind article --id ID --out source.json` 取得，保留其来源和句子顺序后选句；不要把文章 ID 当作新故事自行编写。文章详情页是 `/tools/articles/{id}`。

## 工作流

### Step 1 · 备好句子

三种来源：

1. **mandarinai-reader 的文章** → 从正文挑主线句子（不是全文照搬）
2. **用户给的故事 / 句子** → 直接用
3. **一个话题** → 先按目标水平写一个 3–8 句的小故事（水平边界照 mandarinai-reader 的 leveling）

要求：3–12 句（超过 20 句脚本拒绝）；单句 ≤ 24 字（超了拆短，脚本会警告）；每个汉字一个小写声调拼音音节；每句一条译文。写成 story JSON——结构见 `examples/story-example.json`，全部字段（level / subtitle / cta / bgm / width…）看 `python3 scripts/build-video.py --help`。

### Step 2 · 构建工程

```bash
cd <SKILL_ROOT>
python3 scripts/build-video.py /tmp/story.json --out ~/Documents/mandarin-videos/{YYYYMMDD}-{slug}
```

- 默认逐句取 Swan `/tts?text=...` 并用 ffprobe 实测时长排时间轴；本地 Swan 可设 `--tts-base http://localhost:3000/tts?text=`。这是 `/tts`，不是 `/api/tts`。无音频草稿显式用 `--no-audio`（按字数估时），交付标明无朗读；不能把取音失败静默降级
- 脚本校验：拼音数 = 汉字数、声调符号（拒绝 chuang2）、译文必填、总时长 >90s 告警
- 目标目录已存在会拒绝——每次构建用新目录，确认才 `--force`
- `bgm` 字段可选，只用用户提供的、有权使用的音频文件

### Step 3 · 检查并渲染

```bash
cd <SKILL_ROOT>
npx hyperframes check <out> --json     # 阅读实际 lint/runtime/layout/contrast 结果并修复问题
npx hyperframes render <out> --output <out>/renders/story-v1.mp4 --workers 1
```

check 报什么修什么（字体、溢出、对比度——改输入后重建，或修改生成工程内 HTML）。不要为修一条视频改安装目录的模板。重渲染文件名递增 `-v2` `-v3`，**不覆盖旧成片**。

### Step 4 · 验证交付

- `ffprobe <mp4>`：时长 ≈ 构建输出、1080×1440、有音频流（audio 模式）
- 抽帧看排版：`ffmpeg -ss <秒> -i <mp4> -frames:v 1 /tmp/frame.png`，看 2–3 帧——注音齐、译文出现、没溢出
- 报告：文件路径、时长、句数、有无 BGM/朗读；生词可提示接 mandarinai-flashcard
- 逐字点亮是根据整句音频时长均分的近似节奏，未做逐字强制对齐；不要称为精确逐字同步

## 依赖（一次性）

```bash
cd <SKILL_ROOT>
npm install            # gsap + hyperframes
brew install ffmpeg    # TTS 定时 + 抽帧验证（--no-audio 模式可免）
```

首次渲染 hyperframes 会自下载渲染用浏览器。

## 约束

- 拼音、译文错一个字误导一个学生——不确定的注音先查证；句子内容忠于上游素材，不编造
- 句子水平要一致：超纲句按 leveling 原则改写或拆短，不硬塞
- 工程和成片写到 `~/Documents/mandarin-videos/` 或用户指定位置，不要写进 skill 目录
- 不覆盖已有工程目录和成片；BGM 不自动配，只用用户有权使用的音频

## 运行环境适配

- **Claude Code / Codex / Gemini CLI**：全部走 shell 脚本，无平台专用工具
- **Gemini CLI 沙箱**：`~/Documents/mandarin-videos/` 在工作区外——启动时 `--include-directories ~/Documents/mandarin-videos`，或让用户指定工作区内的输出目录
