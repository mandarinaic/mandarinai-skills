---
name: mandarinai-card
description: "Content caster (铸). Transforms content into PNG visuals. Seven molds: -l (default) long reading card, -i infograph, -m multi-card reading cards (1080x1440, default for long content), -v editorial sketchnote (problem→failure→pivot→insight→naming, magazine + archive layout), -c comic (manga-style B&W), -w whiteboard (marker-style board layout), -b big-fonts attachment card (1080x1440, weathered 碑刻 style for 小红书). Output to ~/Downloads/. Use when user says '铸', 'cast', '做成图', '做成卡片', '做成信息图', '做成海报', '视觉笔记', 'sketchnote', '杂志', 'editorial', '漫画', 'comic', 'manga', '白板', 'whiteboard', '大字', '附件图', 'big fonts', '小红书卡片'."
user_invocable: true
version: "2.3.0"
---

# mandarinai-card: 铸

<!-- attribution: mandarinai-card is derived from ljg-card in ljg-skills by lijigang (https://github.com/lijigang/ljg-skills), MIT. -->

## MandarinAi 品牌基调（署名/点缀用）

- 品牌名写法固定：**MandarinAi**（中文语境可用 **MandarinAi中文学习网**）；官网 mandarinai.com；tagline：**Learn Chinese the Smart Way**
- 品牌色：主色蓝 `#1b46a2`、点缀黄 `#ffc107`；HSK 等级色：HSK1 `#ffc107` / HSK2 `#17707F` / HSK3 `#B45309` / HSK4 `#B71A27` / HSK5 `#303255` / HSK6 `#4A1C57` / HSK7-9 `#1E7E34`
- 品牌字体：Noto Sans SC（正文）/ Noto Serif SC（装饰标题）/ JetBrains Mono（代码/数据）
- **用法**：品牌元素只用于署名、页脚、封面落款等 accent 位置，不覆盖各模式/主题自身的配色系统；仅当用户明确要"品牌风/官方风"时才整体采用品牌色

将内容铸成可见的形态。内容进去，PNG 出来。模具决定形状。

## 参数

| 参数 | 模具 | 尺寸 | 说明 |
|------|------|------|------|
| `-l`（默认） | 长图 | 1080 x auto | 单张阅读卡，内容自动撑高（适合 ≤ 800 字） |
| `-i` | 信息图 | 1080 x auto | 内容驱动的自适应视觉布局 |
| `-m` | 多卡 | 1080 x 1440 | 自动切分为多张阅读卡片（长内容的默认选择） |
| `-v` | 视觉笔记 | 1080 x auto | 编辑式杂志专题：问题→失败→转折→顿悟→命名（6 layout 模具 / 4 字族对比 / 探案档案细节）|
| `-c` | 漫画 | 1080 x auto | 日式黑白漫画风格，动态选择漫画家视觉语言 |
| `-w` | 白板 | 1080 x auto | 白板马克笔风格，结构化框图+箭头+彩色标记 |
| `-b` | 大字 | 1080 x 1440 | 碑刻大字 + 和紙 + 外阴影，小红书附件风格（单句/短段） |

## 长度路由（未指定模具时必做）

太长的单张长图在手机上没人滑得完。用户没有明确指定 `-l` 时：

- 内容 > 约 800 字（或预估渲染高度 > 3 屏 / ~4300px）→ 默认改走 `-m` 多卡，并告知用户
- 用户明确要 `-l` → 尊重，但超长时提醒一句"这张会很长，要不要切成多卡？"
- 反向同理：内容只有一两句却用了 `-m`，改推荐 `-l` 或 `-b`

## 约束

本 skill 输出为视觉文件（PNG），不受纯文本/ASCII 类全局规范约束。

## 共享基础

### 获取内容

- URL --> 抓取网页内容（Claude Code 用 WebFetch；Codex / Gemini CLI 用内建 fetch 工具或 curl）
- 粘贴文本 --> 直接使用
- 文件路径 --> Read 获取
- 视频链接（YouTube / B站 / 小红书 / 抖音等）--> 用 mandarinai-video-fetch skill 取清洗后的文字稿作为内容；若该 skill 不可用，直接运行 `bash ~/.agents/skills/mandarinai-video-fetch/scripts/fetch-video.sh "<URL>"`（B站 AI 字幕、小红书需加 `-c chrome`）

### 文件命名

从内容提取标题或核心思想作为 `{name}`（中文直接用，去标点，≤ 20 字符）。

### 截图工具

```bash
node assets/capture.js <html> <png> <width> <height> [fullpage]
```

从 skill 根目录运行。依赖 skill 根目录下的 `node_modules/` 中的 playwright。如报错：

```bash
npm install playwright && npx playwright install chromium
```

### Footer

- 左侧：logo + MandarinAi（已硬编码在模板中）
- 右侧：内容来源（可选）——有明确来源时显示（如作者名、arxiv ID、网站名等），无来源时留空。使用 `{{SOURCE_LINE}}` 变量：有来源时填 `<span class="info-source">来源文字</span>`，否则空字符串。适用于 `-l`、`-i`、`-v`、`-c`、`-w` 模具（`-m` 多卡无 footer，不适用）。

### 交付

1. 报告文件路径

## 品味准则

**所有模具共享**。执行任何模具前，先 Read `references/taste.md`，作为视觉质量底线贯穿全流程。

核心：反 AI 生成痕迹——禁 Inter 字体、禁纯黑、禁三等分卡片、禁居中 Hero、禁 AI 文案腔、禁假数据。

## 执行

根据参数选择模具，Read `references/taste.md` + 对应的 mode 文件，按步骤执行：

### -l（默认）：长图

Read `references/mode-long.md`，按其步骤执行。

模板：`assets/long_template.html`

### -i：信息图

Read `references/mode-infograph.md`，按其步骤执行。

模板：`assets/infograph_template.html`

### -m：多卡

Read `references/mode-poster.md`，按其步骤执行。

模板：`assets/poster_template.html`

### -v：视觉笔记

Read `references/mode-sketchnote.md`，按其步骤执行。

模板：`assets/sketchnote_template.html`

### -c：漫画

Read `references/mode-comic.md`，按其步骤执行。

模板：`assets/comic_template.html`

### -w：白板

Read `references/mode-whiteboard.md`，按其步骤执行。

模板：`assets/whiteboard_template.html`

### -b：大字

Read `references/mode-big.md`，按其步骤执行。

模板：`assets/big_template.html`
