# 模板目录与选型

六个内置模板都是可直接渲染的完整示例。用法：拷贝到工作目录 → 改文案/数据/颜色 → 保持视觉签名。

## glitch-title.html · 故障艺术标题

- **签名**：cyan/magenta 像散偏移、CRT 扫描线、SVG turbulence 颗粒、角落 ASCII 噪点、REC 角标
- **适合**：片头、转场卡、发布 "system online" 时刻、cyberpunk / 科技攻防主题
- **改造点**：主标题（短词最佳，如 "SIGNAL_LOST"）、顶部频道行、副标语
- **避免**：长句标题——glitch 效果在 3-8 个字符的大字上最狠

## liquid-hero.html · 极光流体 Hero

- **签名**：4 个大色斑 blur(70px) + screen 混合漂浮（紫/粉/青）、暗紫底、细网格、mix-blend-difference 文字
- **适合**：产品亮相、宣言式大声明、AI/创意类主题
- **改造点**：标题、chip 标签、blob 配色（保持同族亮色，别超过 4 个）

## light-leak-cinema.html · 胶片漏光

- **签名**：2.39:1 影院画幅、暖橙漏光 radial-gradient、胶片颗粒、竖划痕、齿孔条、衬线字
- **适合**：情绪化叙事、品牌片、"安静的一年" 式回顾、人文内容
- **改造点**：标题（衬线，可中文）、字幕行、漏光位置（改 radial-gradient 的坐标）

## data-chart-nyt.html · 报纸风数据图

- **签名**：米白纸底、衬线大标题、SVG 折线 stroke-dashoffset 画线动画、标注点、来源行
- **适合**："这个数字涨/跌了" 的故事、趋势叙事、报告摘要
- **改造点**：数据点（SVG path 要按真实数据重算）、标题、轴标签、标注文案
- **注意**：数据必须真实，来源行必须写——这是这个风格的全部可信度

## text-cursor.html · 终端打字机

- **签名**：等宽字体逐字打出 + 方块光标闪烁（光标是 infinite，打字是有限次）
- **适合**：代码/CLI 演示、命令揭示、开发者向内容
- **改造点**：打字内容（JS 字符串数组）、提示符、配速

## logo-outro.html · Logo 收尾

- **签名**：干净的居中 logo 缩放入场 + 副标淡入，纯色底
- **适合**：任何片子的最后一个场景
- **改造点**：logo（文字或 SVG）、tagline、底色与品牌色

## 没有合适模板时

按 `authoring.md` 的规则从零写场景。更多风格可从上游搬运（保留 attribution 注释）：
nexu-io/html-video `templates/`（Apache-2.0，含 kinetic-type、swiss-grid、vignelli、warm-grain、
decision-tree、bold-poster 等 15 个，部分是多合成 GSAP 结构，需按其 compositions 约定处理）。
