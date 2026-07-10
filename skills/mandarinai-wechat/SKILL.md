---
name: mandarinai-wechat
description: "微信公众号写作。把一个选题/链接/视频写成一篇能在公众号发出去的完整文章——钩子开头、可扫读的排版、加粗金句、一个真观点、引导关注/在看/转发的结尾，再配 3-5 个标题候选。可选：用 Chrome CDP 把成稿灌进公众号编辑器存草稿（不需要 API key，个人订阅号也能用）。Use when user asks to 写公众号、写一篇推文、把这个写成公众号文章、公众号怎么写、起公众号标题、发到公众号/灌进公众号编辑器, or says 公众号, WeChat article, 推文."
version: "1.0.0"
---

# 公众号写作

<!-- attribution: title formulas + CJK 排版/标题思路、Chrome-CDP 发布思路参考 baoyu-skills by JimLiu (https://github.com/JimLiu/baoyu-skills), 写作姿态沿用 mandarinai-writes。发布实现为本仓库自写（Playwright connectOverCDP），非 baoyu 代码移植。 -->

## MandarinAi 品牌基调（署名/点缀用）

- 品牌名写法固定：**MandarinAi**（中文语境可用 **MandarinAi中文学习网**）；官网 mandarinai.com；tagline：**Learn Chinese the Smart Way**
- 品牌色：主色蓝 `#1b46a2`、点缀黄 `#ffc107`；HSK 等级色：HSK1 `#ffc107` / HSK2 `#17707F` / HSK3 `#B45309` / HSK4 `#B71A27` / HSK5 `#303255` / HSK6 `#4A1C57` / HSK7-9 `#1E7E34`
- 品牌字体：Noto Sans SC（正文）/ Noto Serif SC（装饰标题）/ JetBrains Mono（代码/数据）
- 官方 logo：横版字标 `mandarinai-illustration/assets/brand/mandarinai-logo.png`（2600×1000 透明底）、方形 icon `mandarinai-illustration/assets/brand/mandarinai-icon.png`（1000×1000 透明底）；卡片署名头像用 `mandarinai-card/assets/logo.png`（460×460 白底圆裁安全版）
- **用法**：品牌元素只用于署名、页脚、封面落款等 accent 位置，不覆盖各模式/主题自身的配色系统；仅当用户明确要"品牌风/官方风"时才整体采用品牌色

把一个选题写成一篇**真的能发出去**的公众号文章：有人愿意点开（标题/开头），有人读得下去（排版/节奏），有人记得住（金句/观点），有人愿意往下走一步（结尾引导）。

不是观点小论文（那是 [mandarinai-writes]）。公众号是对着手机屏幕、随时会划走的人写——钩子要狠、段落要短、观点要真。

## 输入

写作对象可以是：

- **一个选题 / 一段想法** → 直接写
- **文章 / 网页链接** → 抓正文（Claude Code 用 WebFetch；Codex / Gemini CLI 用内建 fetch 或 `curl`），提炼可写的角度，与用户确认后再写。**抓不到就停**，见下
- **视频链接**（YouTube / B站 / 小红书 / 抖音）→ 用 `mandarinai-video-fetch` skill 取清洗后的文字稿；不可用时跑 `bash <mandarinai-video-fetch 目录>/scripts/fetch-video.sh "<URL>"`（skill 目录视安装方式而定：~/.claude/skills/、~/.agents/skills/ 或各 CLI 的插件目录）（B站 AI 字幕、小红书加 `-c chrome`）。从文字稿里挑一个最值得写的角度，不要复述整条视频

### 抓不到正文时（重要）

链接抓取会失败：付费墙、登录墙、纯 JS 渲染、403/反爬（小红书、知乎、部分 mp.weixin 链接尤其常见），或返回的是报错页/几乎空白。

**铁律：抓不到，就不写。** 绝不能凭标题 + 记忆「脑补」一篇出来——那是编造，不是改写，对改写任务是最坏结果。

先**核实抓到的是不是真正文**：明显是登录/报错页、字数远少于一篇文章、只有导航没有正文 → 都算失败。

失败时按顺序：

1. 再试一种方式：换 `curl -L -A "Mozilla/5.0 ..."` 带 UA；或走 reader 代理 `curl -L https://r.jina.ai/<原始URL>`；或找网页快照（archive.org）
2. 还不行 → **停下来如实告诉用户「这个链接抓不到正文（原因）」**，并请他二选一：
   - 直接把正文**粘贴**给我
   - 给一个能抓到的镜像/快照链接
3. 在拿到真实正文之前，**不产出任何文章**，也不猜测它写了什么

**先确认一件事**：这篇是给谁看的、要让他读完做什么（关注 / 转发 / 收藏 / 下单 / 改变一个看法）。目的不同，钩子和结尾就不同。用户没说就用 `AskUserQuestion` 问一句，别替他猜。

## 一篇公众号文章的骨架

```
标题      <- 决定有没有人点开（占成败一半）
开头钩子   <- 前 3 句留住人，否则前功尽弃
正文       <- 小标题分段，一段一个意思，能扫读
金句       <- 全文 2-4 句加粗，是会被截图转发的那几句
结尾       <- 落点 + 一个明确的下一步（关注/在看/转发）
配图建议   <- 封面 + 文中配图位置，概念/角色图默认 MandarinAi 角色 IP（见 mandarinai-illustration 的 references/characters.md），实景图走图库（Pexels/Unsplash/Pixabay）
```

## 标题

标题决定一半成败。每次产出 **4-5 个候选**，让用户挑：

1. 按文章内容、语气挑 **2-3 个最贴的钩子式标题**
2. 再给 **1-2 个朴实标题**（描述式 / 断言式，准确不花哨）
3. 用户指定了方向（如「要悬念感」）就优先那个方向

把最强的钩子放第一个、标 `(推荐)`，用 `AskUserQuestion` 给用户挑。8 种钩子套路、标题原则、禁用模式见 [references/title-formulas.md](references/title-formulas.md)。

一句话原则：**钩子在前 5 个字**，具体压过抽象（「150 行」胜过「一份文档」），口语胜过书面，≤ 20 字防截断，**能兑现**——标题敢说，正文必须接得住。

## 开头

前三句决定读者划不划走。公众号没有「自古以来」「随着……的发展」的预算。

四种能用的开法（挑一种，别叠）：

- **场景**：把读者扔进一个具体画面，他在里面看见自己
- **反差**：先说一个大家默认的事，下一句把它掀翻
- **痛点**：戳一句他正头疼、嘴上没说出口的事
- **结论前置**：直接把最反直觉的结论甩出来，让他想知道凭什么

开头**不交代背景、不自我介绍、不预告结构**（别写「今天我们来聊聊」）。第一句就得有信息或情绪。

## 正文

对着手机屏幕写。

- **一段一个意思**，段落短——3-4 行顶天，长段在手机上是一堵墙
- **小标题切块**，让人扫一眼就知道讲到哪了；小标题要具体、有信息（「3 天搞定 vs 传统方案」胜过「方案对比」）
- **加粗金句**：全文 2-4 句，是读者会划线、会截图发朋友圈的那几句——加粗它们，别整段加粗
- 并列的东西拆成列表，对比的东西用表格——埋在长句里的结构挖出来
- **一篇只立一个真观点**。可以有铺垫、有让步、有转折，但读完只留下一句话
- 长度看选题：观点文 1500-2500 字，干货/教程可到 3000+。判断标准不是字数，是「有没有一句废话」

排版细节（中英文之间空格、全角标点、加粗语法）见 [references/wechat-format.md](references/wechat-format.md)。

## 结尾

公众号的结尾不是总结，是**递一把手**——告诉读者下一步去哪。

1. **落点**：最后一个判断，或一扇门。短，有节奏，留得住
2. **一个明确动作**，且只一个：关注 / 在看 / 转发 / 留言 / 点开链接。多个等于没有
3. 引导要顺，从内容里长出来——别硬接「喜欢就点个在看」。好的引导是「如果这篇帮你省了三个月，转给那个还在踩坑的人」

## 语言与姿态

外科医生的手，朋友的口。冷静下刀，平常说话。沿用 [mandarinai-writes] 的语言纪律：

- 能两个字说的不用四个字。砍机械连词、形容词通胀、软化词
- 翻译腔免疫：这句翻成英文再翻回来，还一样吗？是 → 重写
- 心里放一个具体的人，写给他，不写给「各位读者」
- 不借势、不代言（「程序员都知道」）、不编经历、不自标深度（删掉「再深入一层」，让下一句内容自己显出深度）
- 公众号可以更口语、更有情绪，但**不煽**：情绪从事实里长出来，不是形容词堆出来的

## 磨

初稿出来后，逐项过：

1. **手机扫读**：想象在地铁上用手机划——有没有哪段是一堵墙？哪句话让你想划走？
2. **钩子检验**：只看标题 + 前三句，你会点开吗、会读下去吗？不会 → 重写开头
3. **金句检验**：有没有 2-4 句是你愿意截图发朋友圈的？没有 → 还不够狠，回去切
4. **AI 痕迹过滤**：拐杖词、宣传腔、夸大象征（「标志着」「见证了」「赋能」「充满活力」）全删
5. **一个观点检验**：读完只剩一句话吗？剩两句 → 砍掉弱的那个
6. **兑现检验**：标题答应的，正文给了吗？没给 → 改标题或补正文

## 中文重写

初稿完成后，合上它，用中文读者的眼睛再写一遍——不是翻译，是重写。从句拆开，嵌套展平；主语不必逐句给；节奏、对仗、四字短语该用就用。两稿并看，挑更好的那句。

## 输出

1. 初稿 + 中文重写择优，得到正文
2. 4-5 个标题候选，用 `AskUserQuestion` 让用户定标题
3. 正文末尾附 **配图建议**：封面方向 + 文中 1-3 处配图位置和内容方向。**概念/角色类配图默认走 MandarinAi 角色 IP**——品牌有 19 个成体系的角色（12 生肖学习伙伴 + 7 位人类学习者/导师），每处配图从中选一个最贴的角色、让它成为该处概念的动作主体。生成交给 **mandarinai-illustration** skill：按其 `references/characters.md` 选角（casting guide），用角色定案图做 `--ref` 保持形象一致：

   ```bash
   node <mandarinai-illustration>/scripts/generate-image.mjs \
     --ref <mandarinai-illustration>/assets/characters/<角色>.jpg \
     --prompt "<角色名 + 场景动作 + match the reference sheet exactly>" --ratio 16:9 --out assets --name <语义名>
   ```

   需要 `OPENAI_API_KEY` 或 `GEMINI_API_KEY`；**没有 key 时不硬画**——把每处配图的角色选择 + 完整 prompt 写进配图建议交付（用户可自行生成），或改用纯排版分隔（题图卡/金句卡由 mandarinai-wechat-layout 组件承担）。用户说不要角色或指定别的风格，就按用户的来

   **实景类配图走图库**——当配图位置需要的是实拍照片而非概念图（地点 / 街景 / 食物 / 产品 / 氛围实景，角色隐喻套不上的），且环境里有 `PEXELS_API_KEY` / `UNSPLSH_API_KEY` / `PIXABAY_API_KEY` 中至少一个，用图库脚本取图：

   ```bash
   node scripts/fetch-stock-image.mjs --query "<关键词>" --orientation landscape --out assets --name <语义名>
   ```

   默认按 Pexels → Unsplash → Pixabay 顺序尝试（Pexels 支持中文关键词，国内场景优先）；先 `--list` 看候选再 `--index N` 下载。来源会自动记进 `assets/SOURCES.md`；交付时告知用户图片来自图库、由用户决定是否可用。概念/观点类配图仍然默认 MandarinAi 角色，不要用图库照片硬凑
4. `date "+%Y-%m-%d %H:%M"` 取日期
5. 写入 `~/Documents/notes/{YYYYMMDD}-{标题关键词}.md`（关键词 ≤ 12 字去标点；用户指定位置则优先），frontmatter：

   ```
   ---
   title: {选定标题}
   date: {YYYY-MM-DD HH:MM}
   tags: [wechat]
   author: MandarinAi
   ---
   ```

6. 报告路径，并提示可接力（都不要自动做，等用户说）：
   - **排版**：`mandarinai-wechat-layout`（6 套主题组件库，Markdown → 粘贴不掉样式的公众号 HTML）
   - **封面**：`mandarinai-social-card`（公众号 21:9 + 1:1 封面对）
   - **文中卡片 / 长图**：`mandarinai-card`
   - **发布**：可选，见下

## 发布到公众号（可选）

写作是本 skill 的本体。用户明确要「发到公众号 / 灌进编辑器」时，才走这一步——**只在用户要求时**，不主动发起。

两条路，都不需要 AppID/AppSecret（个人订阅号也能用）：

- **只要 HTML**（最稳）：要主题化排版（章节编号/关键词下划线/引言卡，6 套主题）用 `mandarinai-wechat-layout` skill，产出带「复制」按钮的预览页；要最简朴素样式则 `node scripts/md-to-wechat-html.mjs <article.md> -o out.html`，得到内联样式、可直接全选粘进编辑器的 HTML。
- **Path B · Chrome CDP**：脚本连上你**已登录、已打开文章编辑器**的 Chrome，自动填标题/正文、留成草稿（**永不发表**，配图和发表由用户手动收尾）。

  ```bash
  cd skills/mandarinai-wechat && npm install          # 一次性
  node scripts/publish-wechat.mjs <article.md> --port 9222 [--save-draft]
  ```

完整前置步骤（带远程调试启动 Chrome、扫码登录、新建文章）、分工和排障见 [references/publish.md](references/publish.md)。登录、扫码、点「发表」永远是人来做，脚本只干填表的体力活。

[mandarinai-writes]: ../mandarinai-writes/SKILL.md
