---
name: mandarinai-ppt
description: 生成横向翻页网页 PPT（单 HTML 文件），含 WebGL 背景、章节幕封、数据大字报、图片网格等模板。提供两种风格：① "电子杂志 × 电子墨水"（衬线 + 流体背景 + 暖色） ② "瑞士国际主义"（无衬线 + 网格点阵 + IKB/柠檬黄/柠檬绿/安全橙高亮）。当用户需要制作分享 / 演讲 / 发布会风格的网页 PPT，或提到"杂志风 PPT"、"瑞士风 PPT"、"Swiss Style"、"horizontal swipe deck"时使用。
version: "1.0.0"
---

# Magazine Web Ppt

<!-- attribution: mandarinai-ppt is derived from guizang-ppt-skill by 歸藏 (https://github.com/op7418/guizang-ppt-skill), AGPL-3.0, see LICENSE. Keep this notice in the skill; never write it into generated PPT/HTML/covers. -->

## MandarinAi 品牌基调（署名/点缀用）

- 品牌名写法固定：**MandarinAi**（中文语境可用 **MandarinAi中文学习网**）；官网 mandarinai.com；tagline：**Learn Chinese the Smart Way**
- 品牌色：主色蓝 `#1b46a2`、点缀黄 `#ffc107`；HSK 等级色：HSK1 `#ffc107` / HSK2 `#17707F` / HSK3 `#B45309` / HSK4 `#B71A27` / HSK5 `#303255` / HSK6 `#4A1C57` / HSK7-9 `#1E7E34`
- 品牌字体：Noto Sans SC（正文）/ Noto Serif SC（装饰标题）/ JetBrains Mono（代码/数据）
- 官方 logo：横版字标 `mandarinai-illustration/assets/brand/mandarinai-logo.png`（2600×1000 透明底）、方形 icon `mandarinai-illustration/assets/brand/mandarinai-icon.png`（1000×1000 透明底）；卡片署名头像用 `mandarinai-card/assets/logo.png`（460×460 白底圆裁安全版）
- **用法**：品牌元素只用于署名、页脚、封面落款等 accent 位置，不覆盖各模式/主题自身的配色系统；仅当用户明确要"品牌风/官方风"时才整体采用品牌色

## 这个 Skill 做什么

生成一份**单文件 HTML**的横向翻页 PPT，提供两种可选的视觉基调：

### 风格 A · 电子杂志 × 电子墨水（默认）

- **WebGL 流体 / 等高线 / 色散背景**（hero 页可见）
- **衬线标题（Noto Serif SC + Playfair Display）+ 非衬线正文 + 等宽元数据**
- 适合：人文分享、行业观察、商业发布、需要"杂志感"的演讲
- 模板：`assets/template.html` · 主题色：`references/themes.md` · 布局：`references/layouts.md`
- 美学锚点：像 *Monocle* 杂志贴上了代码

### 风格 B · 瑞士国际主义（Swiss Style）

- **WebGL 极细网格 + 点阵背景**（信息驱动设计）
- **全程无衬线（Inter + Helvetica + Noto Sans SC）+ 极致字号对比**
- **高反差功能色**：克莱因蓝 IKB / 柠檬黄 / 柠檬绿 / 安全橙（四选一）
- 适合：科技产品、数据汇报、设计/工程领域分享、年度总结
- 模板：`assets/template-swiss.html` · 主题色：`references/themes-swiss.md` · 布局：`references/layouts-swiss.md`
- 美学锚点：像 Massimo Vignelli + Helvetica Forever

**两种风格共享**：横向翻页（键盘 ← →、滚轮、触屏、ESC 索引）、Lucide 图标、Motion One 入场动效（本地 + CDN 双保险）。

## 何时使用

**合适的场景**：
- 线下分享 / 行业内部讲话 / 私享会
- AI 新产品发布 / demo day
- 带有强烈个人风格的演讲
- 需要"一次做完，不用翻页工具"的网页版 slides

**不合适的场景**：
- 大段表格数据、图表叠加（用常规 PPT）
- 培训课件（信息密度不够）
- 需要多人协作编辑（这是静态 HTML）

## 工作流

### Step 1 · 需求澄清(**动手前必做**)

**如果用户已经给了完整的大纲 + 图片/截图处理要求**,可以跳过直接进 Step 2。

**如果用户只给了主题或一个模糊想法**,用这 7 个问题逐个对齐后再动手。不要基于猜测就开始写 slide——一旦结构定错,后期翻修代价很高:

#### 运行环境适配

- **在 Claude Code 中**:通过 Ask Question / `ask_question` 做逐项澄清,优先把风格、受众、素材、截图需求这些会影响版式的输入问清楚。
- **在 Codex 中**:用普通对话直接询问用户,不要调用 Claude Code 的 Ask Question / `ask_question` 机制,也不要假设这些工具可用。一次最多问 1-3 个最关键问题;如果信息缺口不影响开工,先做合理假设并在回复里说明。

#### 7 问澄清清单

| # | 问题 | 为什么要问 |
|---|------|-----------|
| 1 | **风格 A 还是 B?**(电子杂志风 / 瑞士国际主义风) | **必须先问**,决定用哪个 template + layouts + themes 文件 |
| 2 | **受众是谁?分享场景?**(行业内部 / 商业发布 / demo day / 私享会) | 决定语言风格和深度 |
| 3 | **分享时长?** | 15 分钟 ≈ 10 页,30 分钟 ≈ 20 页,45 分钟 ≈ 25-30 页 |
| 4 | **有没有原始素材?**(文档 / 数据 / 旧 PPT / 文章链接 / 视频链接) | 有素材就基于素材,没有就帮他搭;视频链接先用 mandarinai-video-fetch skill 转成文字稿再当素材用(不可用时运行 `bash <mandarinai-video-fetch 目录>/scripts/fetch-video.sh "<URL>"`（skill 目录视安装方式而定：~/.claude/skills/、~/.agents/skills/ 或各 CLI 的插件目录）) |
| 5 | **有没有图片或截图?希望怎么处理?** | 决定图文版式、图片槽位、截图是否需要 CleanShot X 式适配或 GPT-M 2.0 重构 |
| 6 | **想要哪套主题色?** | 杂志风 5 套(`themes.md`) / 瑞士风 4 套(`themes-swiss.md`),挑一 |
| 7 | **有没有硬约束?**(必须包含 XX 数据 / 不能出现 YY) | 避免返工 |

#### 风格选择参考(问题 1)

| 如果用户说... | 推荐风格 |
|---|---|
| "杂志感" / "人文" / "Monocle 风" / 不指定 | **A · 电子杂志风** |
| "瑞士风" / "Swiss Style" / "Helvetica" / "极简" / "网格" / "信息图" / "数据驱动" | **B · 瑞士国际主义风** |
| 内容是 AI 产品 / 技术 / 工程 / 数据汇报 | B 更合适 |
| 内容是行业观察 / 人文 / 故事 / 文化 | A 更合适 |
| 用户给了大量 KPI 数字 / 路线图 / 流程 | B 更合适(`Data Hero` 布局是瑞士风专长) |
| 用户给了大量纪实照片 / 人文图片 | A 更合适(图片网格、左文右图是杂志风专长) |
| 用户需要 GPT-M 2.0 生成截图再设计 / 信息图 / 证据墙 | B 也很合适(S22 主图、S15/S16 图片网格可以承载证据图) |

#### 大纲协助(如果用户没有大纲)

用"叙事弧"模板搭骨架,再填内容:

```
钩子(Hook)       → 1 页   : 抛一个反差 / 问题 / 硬数据让人停下来
定调(Context)    → 1-2 页 : 说明背景 / 你是谁 / 为什么讲这个
主体(Core)       → 3-5 页 : 核心内容,用 Layout 4/5/6/9/10 穿插
转折(Shift)      → 1 页   : 打破预期 / 提出新观点
收束(Takeaway)   → 1-2 页 : 金句 / 悬念问题 / 行动建议
```

叙事弧 + 页数规划 + 主题节奏表(见 `layouts.md`),**三张表对齐后**再进 Step 2。

大纲建议保存为 `项目记录.md` 或 `大纲-v1.md`,便于后续迭代。

#### 图片约定(告知用户)

在动手前向用户说清:

- **文件夹位置**:`项目/XXX/ppt/images/` 下(和 `index.html` 同级)
- **命名规范**:`{页号}-{语义}.{ext}`,例如 `01-cover.jpg` / `03-figma.jpg` / `05-dashboard.png`
  - 页号补零便于排序
  - 语义用英文,短、具体、和内容对应
- **规格建议**:
  - 单张 ≥ 1600px 宽(避免大屏模糊)
  - JPG 用于照片/截图,PNG 用于透明 UI/图表
  - 总大小控制在 10MB 内(影响翻页流畅度)
- **如何替换**:保持**同名覆盖**最稳(HTML 里不用改路径);如果文件名变了,记得全局搜 `images/旧名` 改成新名
- **没图怎么办**:和用户对齐。三条路:① 先用占位色块生成结构,等图片后期补(要告知 layout 4/5/10 等图文混排页没图就没法验证视觉效果);② 实景类槽位(人文纪实 / 风景 / 城市 / 氛围 hero / 图片网格)走图库配图,见下面「图库配图」;③ Codex 环境下用 GPT-M 2.0 生成

#### 图库配图(可选,实景类槽位)

当图片槽位需要的是**实拍照片**(人文纪实 / 风景 / 城市 / 物件 / 氛围 hero、S15/S16 图片网格、左文右图的 quote 配图)而用户没有素材时,可以从 Pexels / Unsplash / Pixabay 图库取图。信息图、流程图、截图再设计、概念图**不走图库**——那些要么用模板画,要么走 GPT-M 2.0;需要**带中文标签的解释图 / 机制图 / 材质化图表**时,交给 `mandarinai-illustration` skill 出图(它负责标签规则、图表数据准确性和材质风格),生成后照常落盘进 `images/` 再引用。

前提:环境里有 `PEXELS_API_KEY` / `UNSPLSH_API_KEY` / `PIXABAY_API_KEY` 中至少一个。用内置脚本下载到本地 `images/`(**保持禁止外链图床的规则不变**——图必须落盘进 `images/` 再引用):

```bash
node <SKILL_ROOT>/scripts/fetch-stock-image.mjs --query "<关键词>" \
  --orientation landscape --out 项目/XXX/ppt/images --name 04-mountain
```

- `--provider auto`(默认)按 Pexels → Unsplash → Pixabay 顺序尝试,缺 key 的自动跳过;Pexels 支持中文关键词,国内场景优先
- `--name` 遵守 `{页号}-{语义}` 命名规范;`--orientation` 按落位槽位选(hero 用 landscape,3:4 小图用 portrait)
- 先 `--list` 看候选(JSON 含来源页、作者、尺寸、alt),再 `--index N` 下载选中的那张
- 脚本会把来源自动记进 `images/SOURCES.md`;交付时告知用户图片来自图库、版权未逐一核实,由用户决定是否可用/是否标注来源
- 图库照片风格必须贴合 deck 风格再用:风格 A 偏纪实/胶片感,风格 B 偏干净/高对比;调性不符宁可用占位色块等用户补图

一个 deck 里图库照片通常 1-4 张就够,不要为凑满槽位而堆图。

#### 截图需求约定(动手前必须问)

只要用户提到产品截图、网页截图、代码截图、设计稿、dashboard、旧 PPT 截图或"帮我美化截图",都要先确认:

- **截图位置**:截图文件在哪个文件夹?是否已经命名好?
- **使用目的**:保真展示 / 截图美化 / 截图再设计 / UI 情景图?
- **落位比例**:最终放进哪个版式槽位?常用 `21:9` / `16:10` / `16:9` / `4:3` / `1:1`
- **内容要求**:是否必须保留全部文字、品牌、数据?是否有敏感信息要遮挡?
- **视觉处理**:是否需要主题背景、留边、居中/角落对齐、拆成长截图面板?

默认策略:先让内容适配模板,再处理图片比例。截图需要保真时,先读 `references/screenshot-framing.md`,优先使用 `assets/screenshot-backgrounds/` 的内置背景资产做程序化 CleanShot X 式背景画布适配;只有原截图太乱、太长、太窄或需要概念化表达时,才用 GPT-M 2.0 做截图再设计。

#### Codex 配图生成(可选)

如果当前运行环境是 **Codex**,完成 deck 初稿后,主动问用户是否需要用 GPT-M 2.0 生成配图并插入 PPT。不要默认生成。

推荐询问方式:

> 要不要为这份 PPT 生成几张配图?可以做成人文纪实照片、杂志风信息图、流程/对比/系统关系图,或把截图再设计成统一的杂志风视觉。

如果用户确认生成,再问他想要哪种图片类型或风格;如果用户没有偏好,根据页面内容自行推荐 1-3 张最值得生成的配图。

如果用户提供的是截图,先判断是**截图美化**还是**截图再设计**:

- 截图美化:读 `references/screenshot-framing.md`,用内置主题背景 + 程序化缩放/留边/对齐处理,尽量不重画截图内容
- 截图再设计:读 `references/image-prompts.md`,按当前版式槽位生成目标比例图片,并保持语言、主题色和边距一致

生成配图时遵守:

- 提示词保持简短,只框定主题、用途、风格和比例,不要写长篇摄影指导
- 图片风格必须贴合当前 deck 风格:风格 A 用"电子杂志 × 电子墨水";风格 B 用"瑞士国际主义 / Swiss Style"
- 信息图、图表、截图再设计里的文字语言必须跟随用户正在使用的语言;中文 deck 用中文,英文 deck 用英文
- 先看 `references/image-prompts.md` 选择图片类型和基础提示词
- 如果处理用户原始截图,先看 `references/screenshot-framing.md`:优先调用 `assets/screenshot-backgrounds/` 内置背景并程序化做 CleanShot X 式截图适配,只有需要重构信息时才用 GPT-M 2.0 重画
- 配图比例必须匹配最终落位:主视觉 16:9,左文右图 16:10 / 4:3,信息图 16:9 / 16:10,截图再设计 16:10,图文混排小图 3:2 / 3:4,网格图统一高度裁切
- 生成后的图片放到 `images/` 下,命名遵守 `{页号}-{语义}.{ext}`

### Step 2 · 拷贝模板

**根据 Step 1 选定的风格,拷贝对应的模板**到目标位置（通常是 `项目/XXX/ppt/index.html`），同时在同级建一个 `images/` 文件夹准备接图片。

```bash
mkdir -p "项目/XXX/ppt/images" "项目/XXX/ppt/assets"

# 风格 A · 电子杂志风
cp "<SKILL_ROOT>/assets/template.html" "项目/XXX/ppt/index.html"

# 或 风格 B · 瑞士国际主义风
cp "<SKILL_ROOT>/assets/template-swiss.html" "项目/XXX/ppt/index.html"

# 两种风格都要:动效引擎本地副本(模板里 import('./assets/motion.min.js') 指向它)
cp "<SKILL_ROOT>/assets/motion.min.js" "项目/XXX/ppt/assets/motion.min.js"
```

两个 `template*.html` 都是**完整可运行**的文件——CSS、WebGL shader、翻页 JS、字体/图标 CDN 全已预设好,只有 `<!-- SLIDES_HERE -->` 占位符等待你填充 slide 内容。

**注意**:风格 A 和 B **不能混用**。layouts.md 里的类（如 `.h-hero` 衬线大标题、`.stat-card` 等）只在 template.html 有定义；layouts-swiss.md 里的类（如 `.kpi-hero`、`.accent-block`、`.span-N`、`.dots` 等）只在 template-swiss.html 有定义。一份 deck 只能选一套。

#### 2.1 · 必改占位符（**容易漏**）

拷贝后立刻改掉以下占位符，否则浏览器 Tab 会显示"[必填] 替换为 PPT 标题"这种尴尬文字：

| 位置 | 原始 | 需改为 |
|------|------|--------|
| `<title>` | `[必填] 替换为 PPT 标题 · Deck Title` | 实际 deck 标题(如 `一种新的工作方式 · Luke Wroblewski`) |

每次拷贝完 template.html 第一件事:grep 一下"[必填]" 确认全部替换完。

#### 2.2 · 选定主题色(5 套预设 · 不允许自定义)

本 skill **只允许从 5 套精心调配的预设里选一套**,不接受用户自定义 hex 值——颜色搭配错了画面瞬间变丑,保护美学比给自由更重要。

| # | 主题 | 适合 |
|---|------|------|
| 1 | 🖋 墨水经典 | 通用 / 商业发布 / 不知道选啥的默认 |
| 2 | 🌊 靛蓝瓷 | 科技 / 研究 / 数据 / 技术发布会 |
| 3 | 🌿 森林墨 | 自然 / 可持续 / 文化 / 非虚构 |
| 4 | 🍂 牛皮纸 | 怀旧 / 人文 / 文学 / 独立杂志 |
| 5 | 🌙 沙丘 | 艺术 / 设计 / 创意 / 画廊 |

**操作**:
1. 基于内容主题推荐一套,或直接问用户选哪一套
2. 打开 `references/themes.md`,找到对应主题的 `:root` 块
3. **整体替换** `assets/template.html`(已拷贝版本)开头 `:root{` 块里标有"主题色"注释的那几行(`--ink` / `--ink-rgb` / `--paper` / `--paper-rgb` / `--paper-tint` / `--ink-tint`)
4. 其他 CSS 都走 `var(--...)`,无需任何其他改动

**硬规则**:
- 一份 deck 只用一套主题,不要中途换色
- 不要接受用户给的任意 hex 值——委婉拒绝并展示 5 套让选
- 不要混搭(例如 ink 取墨水经典、paper 取沙丘)——会彻底违和

### Step 3 · 填充内容

#### 3.0 · 预检:类名必须在模板的 `<style>` 里有定义（**最重要**）

**这是所有生成问题的源头**。layouts 骨架使用了很多类名,如果模板的 `<style>` 里没有对应定义,浏览器会 fallback 到默认样式——大标题字体错、卡片挤成一团、pipeline 糊成一行、图片堆到页面底部。

**两种风格类名互不通用**(再次强调):
- 风格 A 模板里有 `h-hero`(衬线)、`stat-card`、`grid-2-7-5`、`frame` 等
- 风格 B 模板里有 `h-hero`(无衬线)、`kpi-hero`、`accent-block`、`span-N`、`dots`、`grid-12` 等
- 同名 class 在两个模板里**视觉表现完全不同**(例:风格 A 的 `h-hero` 是 Noto Serif SC 衬线,风格 B 的 `h-hero` 是 Inter 无衬线)

**在写任何 slide 代码之前:**

1. **先 Read 当前用的模板**(至少读到 `<style>` 块末尾):
   - 风格 A → `assets/template.html`
   - 风格 B → `assets/template-swiss.html`
2. **对照对应 layouts 文件的 Pre-flight 列表**,确认你要用的每个类都在 `<style>` 里存在
3. 如果某个类缺失:**在模板的 `<style>` 里补上**,不要在每个 slide 里 inline 重写
4. **模板是唯一的类名来源**——不要发明新类名,如需自定义用 `style="..."` inline

**完整类名清单**(逐项对照,不要凭记忆):
- 风格 A → `references/layouts.md` 开头"生成前必读(Pre-flight)"一节
- 风格 B → `references/layouts-swiss.md` 开头"Pre-flight 类名清单"一节(画布 / 排版 / 卡片 / 网格 / 时间线 / 图表 / 装饰 / 版式专属 / 图片混排 / spacing token)

#### 3.0.5 · 规划主题节奏（**和类预检同等重要**)

**在挑布局之前**,必须先列出每一页的主题 class(`hero dark` / `hero light` / `light` / `dark`)并写到文档或草稿里对齐。详细规则看 `references/layouts.md` 开头的"主题节奏规划"一节。

**强制规则**:

- 每页 section 必须带 `light` / `dark` / `hero light` / `hero dark` 之一,不要只写 `hero`
- 连续 3 页以上同主题 = 视觉疲劳,不允许
- 8 页以上必须有 ≥1 个 `hero dark` + ≥1 个 `hero light`
- 整个 deck 不能只有 `light` 正文页,必须有 `dark` 正文页制造呼吸
- 每 3-4 页插入 1 个 hero 页(封面/幕封/问题/大引用)

**生成后自检**:`grep 'class="slide' index.html` 列出所有主题,人工确认节奏合理再交付。

#### 3.1 · 挑布局

**不要从零写 slide**。打开对应的 layouts 文件,里面有 10 种现成布局骨架,每种都是完整可粘贴的 `<section>` 代码块。

**风格 A** → `references/layouts.md`:

| Layout | 用途 |
|---|---|
| 1. 开场封面 | 第 1 页 |
| 2. 章节幕封 | 每幕开场 |
| 3. 数据大字报 | 抛硬数据 |
| 4. 左文右图(Quote + Image) | 身份反差 / 故事 |
| 5. 图片网格 | 多图对比 / 截图实证 |
| 6. 两列流水线(Pipeline) | 工作流程 |
| 7. 悬念收束 / 问题页 | 幕末 / 收尾 |
| 8. 大引用页(Big Quote) | 衬线金句 / takeaway |
| 9. 并列对比(Before / After) | 旧模式 vs 新模式 |
| 10. 图文混排(Lead Image + Side Text) | 信息密集的图文页 |

**风格 B** → 先读 `references/swiss-layout-lock.md`,再读 `references/layouts-swiss.md`。

瑞士主题默认进入 **Swiss locked mode**:

- 正文页只能使用原始参考 PPT 登记的 22 个版式 `S01-S22`;新增首页/尾页只能使用 Skill 明确提供的 `SWISS-COVER-ASCII` / `SWISS-CLOSING-ASCII`。
- 每个 `<section class="slide">` 必须写 `data-layout="Sxx"`。没有 `data-layout` 就视为未登记版式。
- 不允许临时发明 `P23/P24`、`Swiss Image Split`、`Evidence Grid` 这类原始 22P 之外的正文结构,除非用户明确要求实验版式。
- 顶部中文标题默认左对齐、处在左上内容轴。不要把小标题放左列、大标题放右列,造成视觉居中;只有原始 statement/split 版式允许强中心叙事。
- SVG 只负责几何图形。不要在 SVG 里写文字标签,所有标签改用 HTML 网格/卡片/caption。
- 地理/历史/城市路线/地点关系页使用 `S08 + Swiss Map Component`:先读 `references/swiss-map-component.md`,仍保留 `data-layout="S08"`。

原始 22 个正文版式(S01 Index Cover ... S22 Image Hero)的完整登记表——每个版式的用途、必须保留的骨架、图片规则——见 `references/swiss-layout-lock.md` 的「登记版式」一节,选版式时对照那张表,不要凭印象。

**登记扩展**:`S08 + Swiss Map Component` 用于地点、人物住所、路线、城市关系。它不是新 layout,而是 S08 右侧插槽的 MapLibre 地图组件;必须按 `references/swiss-map-component.md` 的点位、连线、卡片和右上角缩放/拖动控制实现。

选对应 layout,粘过去,改文案和图片路径即可。**务必先完成 3.0 预检**。

**风格 B 版式多样性硬规则**:
- 7-8 页 deck 至少使用 **6 个不同 S 编号版式**;10 页以上至少使用 8 个不同版式。
- 如果用户说"测试模板 / 看看效果 / 多一点版式",必须覆盖:一个封面、一个收尾、至少 1 个对比或时间线(S08/S11/S02)、至少 1 个结构图(S14/S17/S15)、至少 1 个图片版式(S22 或 S15/S16 图片格改造)。
- 不允许连续 3 页使用同一种主体结构,例如连续三页 `head + grid + card`。
- 图片页不能偷懒发明新结构。2-3 张图时,用 S15/S16 的原始网格骨架改造成图片格;单张大图用 S22。
- 开写 HTML 前先列一张 `页码 → data-layout → 选用理由 → 图片槽位` 草稿;交付前运行 `node <SKILL_ROOT>/scripts/validate-swiss-deck.mjs index.html`。

#### 3.2 · 图片比例规范

永远用**标准比例**,不要用原图奇葩比例(如 `2592/1798`):

| 场景 | 推荐比例 |
|------|---------|
| S22 顶部主图 | **21:9**;照片关键主体放中央安全区 |
| S15/S16 多图格 | 统一 21:9 或统一 16:10,不能混用 |
| 左文右图 主图(风格 A) | 16:10 或 4:3 + `max-height:56vh` |
| 图片网格(风格 A) | **固定 `height:26vh`**,不用 aspect-ratio |
| 左小图 + 右文字 | 1:1 或 3:2 |
| 全屏主视觉 | 16:9 + `max-height:64vh` |
| 图文混排小插图 | 3:2 或 3:4 |

**默认不要让图片 `align-self:end`**——会滑到页面底部,很容易碰到分页组件。用 grid 容器 + `align-items:start`(template 已预设)让图片贴顶即可;如果确实需要图文底对齐,必须先控制图片高度,再使用模板已有安全区类 `.nav-safe-bottom` / `.nav-safe-bottom-tight`,不要让最低处碰到分页组件。

**风格 B 瑞士风额外规则**:
- 单张大图用 S22;多图测试用 S15/S16 的原始卡片网格改造,不要用未登记的 P23/P24
- 生成图片前先写 `data-image-slot`:例如 `s22-hero-21x9` / `s15-grid-21x9` / `s16-brief-21x9`
- S22 配图默认生成 21:9,提示词必须包含 `subject centered in the safe middle area`;照片容器用 `object-position:center 35%`,不要用 `top center`
- 图片容器必须直角、无阴影、无圆角;默认背景用白色 `var(--paper)`,不要用灰底包白底信息图
- 白底 GPT 信息图/流程图/UI 图默认不要加外框描边,不要随手套 `.swiss-keyline`;需要强调时只用 `.swiss-lined` 的顶部 accent 线
- UI/信息图如果是用户原始截图或文字密集图,才用 `.fit-contain`;如果已按 S15/S16 槽位重生成,必须用 `.frame-img.r-21x9` / `.frame-img.r-16x10` 铺满容器,不要固定 `height:18vh` 后把图缩小
- 多图同组必须统一图片槽位、比例和高度,不能混用
- GPT-M 2.0 生成图使用 `image-prompts.md` 的"风格 B:瑞士国际主义配图规则"
- 任何图片、caption、timeline label、footnote 的最低处都不能进入底部分页区域;需要贴底时用 `.nav-safe-bottom` / `.nav-safe-bottom-tight`,不要手写 `bottom:2vh`

#### 3.2.1 · 中文大标题字号分档(风格 B 必做)

中文方块字视觉面积大,不能直接套英文 hero 的 6.8-7vw。写中文大标题前先分档:

| 标题形态 | 推荐字号 |
|---|---|
| 1 行,≤ 8 个中文字符 | `min(6.4vw,11.2vh)` |
| 2 行,每行≤ 8 个中文字符 | `min(5.8vw,10.2vh)` |
| 2 行,任一行 9-12 个中文字符 | `min(5.2vw,9.2vh)` |
| 3 行或更长 | 优先改写标题;不得已用 `min(4.6vw,8.2vh)` |

如果标题挤占了图片或正文区域,先压缩标题文案,再降字号;不要靠把下方内容推到底来硬塞。

#### 3.2.2 · 瑞士风演示最小字号与字重阶梯(风格 B 必做)

投屏演示的小字不能按网页注释的 10-12px 写:正文 ≥ 18px、卡片描述/caption/图注 ≥ 16px、meta/mono label ≥ 14px。内容放不下就删文案、拆页或换 Sxx 版式,不要压字号。

**字重阶梯**——"越大越细,越小越粗"是具体映射(≥8vw 用 200,16-20px 用 400-500,13-15px 小字用 500-600),同一页内字号小的元素字重必须 ≥ 字号大的;16px 左右禁止 weight 300。完整字号区间 → 字重映射表和 grep 自查命令见 `references/checklist.md` 的 0-S-4 节。

组件细节(字体、颜色、网格、图标、callout、stat-card 等)在 `references/components.md`。

### Step 4 · 对照检查清单自检

生成完一定要打开 `references/checklist.md`，逐项对照。里面总结了**真实迭代过程中踩过的所有坑**，P0 级别的问题（emoji、图片撑破、标题换行、字体分工）必须全部通过。

#### 4.0 · 不只看代码:必须打开网页做视觉核对

代码只能证明类名和结构存在,不能证明版式舒服。生成后必须打开网页逐页看:

1. 同时打开原始参考 PPT、当前模板或生成页、测试 PPT;原始参考是 `assets/template-swiss.html`。
2. 截图前等入场动效稳定(约 1-2 秒),不要把动画中间态当成版式问题。
3. 先看视觉:大标题字重、标题与内容间距、图片是否与正文对齐、图片/说明是否碰到底部分页组件。
4. 再看代码:确认该页选用的版式与内容形状匹配,没有把数据专用版式拿来讲概念,也没有把可选组件堆成装饰。
5. 对照原始参考模板时,以实际页面用法为准,不要只看 CSS helper 定义;原始页面的大字实际多为 200/300,不要被 raw CSS 里的 700/800/900 带偏。
6. 如果页面别扭,先判断是版式选错、必选组件缺失、可选组件滥用,还是间距/安全区问题;不要直接靠加 margin 硬救。

#### 分风格快速必查(逐条过,不要跳)

完整清单在 `references/checklist.md` 开头的「交付前快速必查」一节——风格 A 7 条(衬线大标题、图片网格 `height:Nvh`、标准比例、中文标题 ≤5 字 nowrap、Lucide 不用 emoji、字体分工等),风格 B 24 条(全程无衬线、单一 accent、无渐变/阴影/圆角、大字 weight 200、卡片四类互斥、双约束限高、时间线对齐、动效 recipe、低功耗 B 键、nav 安全区等)。按当前风格把对应清单逐条过完才能交付。

### Step 5 · 本地预览

直接在浏览器打开 `index.html` 就行。macOS 下：

```bash
open "项目/XXX/ppt/index.html"
```

不需要本地服务器。图片走相对路径 `images/xxx.png`。

**动效注意**:`file://` 打开时浏览器会以 CORS 拦截本地 module import,动效自动 fallback 到 jsDelivr CDN(联网即正常)。需要**离线演示**动效时必须走本地服务器:

```bash
cd "项目/XXX/ppt" && python3 -m http.server 8000   # http://localhost:8000
```

### Step 6 · 迭代

根据用户反馈修改——模板的 CSS 已经高度参数化，90% 的调整都是改 inline style（字号 `font-size:Xvw` / 高度 `height:Yvh` / 间距 `gap:Zvh`）。

---

## 资源文件导览

```
mandarinai-ppt/
├── SKILL.md                  ← 你正在读
├── assets/
│   ├── template.html         ← 风格 A · 电子杂志风模板（种子文件）
│   ├── template-swiss.html   ← 风格 B · 瑞士国际主义风模板（种子文件）
│   ├── screenshot-backgrounds/ ← 截图美化内置背景(WebP):style-a 5 套 / style-b 4 套
│   └── motion.min.js         ← Motion One 本地副本（Step 2 拷到 deck 旁,http:// 下本地加载,约 64KB,共用）
├── scripts/
│   └── validate-swiss-deck.mjs ← 风格 B 静态校验:登记版式、图片槽位、SVG 文本、标题对齐
└── references/
    ├── components.md         ← 组件手册（字体、色、网格、图标、callout、stat、pipeline、动效... 风格 A 适用）
    ├── layouts.md            ← 风格 A · 10 种页面布局骨架（可直接粘贴,含动效标记）
    ├── swiss-layout-lock.md  ← 风格 B · 原始 22P 版式锁,正文页必须按这里登记
    ├── layouts-swiss.md      ← 风格 B · 原始 22P 骨架说明 + 少量明确标注的实验区
    ├── swiss-map-component.md ← 风格 B · S08 地图扩展组件(MapLibre 点位/连线/卡片/控制)
    ├── themes.md             ← 风格 A · 5 套主题色预设（只能选不能自定义）
    ├── effects-cinematic.md  ← 风格 A · 可选 hero 页特效（颗粒/漏光/极光/故障/扫描线/打字机）
    ├── themes-swiss.md       ← 风格 B · 4 套瑞士风主题色预设（IKB / 柠檬黄 / 柠檬绿 / 安全橙）
    ├── image-prompts.md      ← GPT-M 2.0 配图类型、比例和基础提示词
    ├── screenshot-framing.md ← CleanShot X 式截图适配语义 + 内置背景资产映射
    └── checklist.md          ← 质量检查清单（P0/P1/P2/P3 分级）
```

**加载顺序建议**：
1. 先读完 `SKILL.md`(这个文件)了解整体
2. Step 1 需求澄清**第一问**先确定风格 A 还是 B,然后:
   - 风格 A:读 `themes.md` 帮用户选一套主题色
   - 风格 B:读 `themes-swiss.md` 帮用户选一套主题色
3. **动手前 Read 对应模板的 `<style>` 块**——这是类名的唯一来源,缺类会导致整页样式崩
   - 风格 A → `assets/template.html`
   - 风格 B → `assets/template-swiss.html`
4. 读对应的 layouts 文件挑布局:
   - 风格 A → `layouts.md`(顶部有 Pre-flight 类名清单、主题节奏规划、动效 recipe 决策树)
   - 风格 B → **先读 `swiss-layout-lock.md`**,再读 `layouts-swiss.md`;正文页必须从 S01-S22 选择,每页写 `data-layout`
5. 如果风格 B 需要地点、路线、人物住所或城市关系地图,读 `swiss-map-component.md`
6. 如果在 Codex 中生成配图,读 `image-prompts.md` 挑图片类型、比例和基础提示词;如果是用户原始截图,先读 `screenshot-framing.md`,优先使用 `assets/screenshot-backgrounds/` 的内置背景资产
7. 细节调整时读 `components.md` 查组件(含 Motion 动效系统章节,主要服务风格 A;风格 B 的组件细节在 `layouts-swiss.md` 附录)
8. 生成后先运行 `node scripts/validate-swiss-deck.mjs path/to/index.html`,再读 `checklist.md` 自检

**动效相关**:模板已把 Motion One 的加载和 recipe 逻辑内嵌到底部 module script。你不需要改 JS,只需要按 `layouts.md` / `layouts-swiss.md` 的骨架在 HTML 里加 `data-anim` / `data-animate` 即可。加载顺序:本地 `./assets/motion.min.js`(Step 2 已拷到 deck 旁,经 `http://` 访问时生效;`file://` 下被浏览器 CORS 拦截)→ jsDelivr CDN → 双双失败时自动降级为"无动画但内容可读"。离线演示见 Step 5 的本地服务器说明。风格 B 模板必须保留 `B` 键低功耗模式:切换后停止 WebGL/ASCII canvas RAF,取消正在运行的 Web Animations,并把当前页内容直接 reveal 到静态最终态。

## 核心设计原则（哲学）

### 风格 A · 电子杂志风（5 轮迭代总结）

> 违反其中任何一条，杂志感都会垮。

1. **克制优于炫技** — WebGL 背景只在 hero 页透出，普通页几乎看不见
2. **结构优于装饰** — 不用阴影、不用浮动卡片、不用 padding box，一切信息靠**大字号 + 字体对比 + 网格留白**
3. **内容层级由字号和字体共同定义** — 最大衬线 = 主标题，中衬线 = 副标，大非衬线 = lead，小非衬线 = body，等宽 = 元数据
4. **图片是第一公民** — 图片只裁底部，保证顶部和左右完整；网格用 `height:Nvh` 固定，不要用 `aspect-ratio` 撑
5. **节奏靠 hero 页** — hero 和 non-hero 交替，才不累眼睛
   - hero 页可选影院级特效（颗粒 / 漏光 / 极光 / 故障），配方与纪律见 `references/effects-cinematic.md`：一份 deck 最多一个特效家族，正文页禁用，风格 B 全部禁用
6. **术语统一** — Skills 就是 Skills，不要中英混合翻译

### 风格 B · 瑞士国际主义风

> 违反其中任何一条，画面瞬间从瑞士掉到 PowerPoint。

1. **单一锚点色** — 一份 deck 只用一个 accent，不允许多色高亮拼贴
2. **极致字号对比** — 主标题与正文比例 ≥ 8:1,KPI 必须是"Data Hero"(屏幕宽度的 18-22%)
3. **无衬线只此一家** — Inter / Helvetica / Noto Sans SC,任何衬线都是错的
4. **直角纯色** — 不允许渐变 / 阴影 / 圆角(rule 横线除外)
5. **网格至上** — 所有元素吸附到 12-col grid,左对齐 + 大幅留白做非对称美学
6. **Hairline 是手术刀** — 1px 的极细分割线就够,不要加粗、不要加阴影
7. **点阵装饰只在 hero 页透出** — 正文页保持纯净底色

## 参考作品(风格锚点)

- **风格 A**:歸藏"一人公司"分享(2026-04-22)、*Monocle* 杂志版式、Garry Tan "Thin Harness, Fat Skills" 博客 demo
- **风格 B**:Massimo Vignelli(NYC Subway / Unimark)、*Helvetica Forever*、Josef Müller-Brockmann 网格系统;当代:Acne Studios / Off-White / IKEA / Beck Design
