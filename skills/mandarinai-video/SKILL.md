---
name: mandarinai-video
description: "Create short animated videos (MP4) from single-file HTML scenes, rendered locally with Playwright + ffmpeg. Six built-in frame styles: glitch title (cyberpunk), liquid aurora hero, light-leak cinematic, NYT-style animated data chart, typewriter terminal text, logo outro. Use when the user asks to 做视频 / 做个片头 / 生成 MP4 / video intro / title card / animated chart video / 转场 / outro, or wants article/deck content turned into a short video. Not for: long-form editing, talking-head video, or fetching existing videos (use mandarinai-video-fetch for that)."
version: "0.1.0"
---

# mandarinai-video

<!-- attribution: render pipeline and bundled templates ported from nexu-io/html-video (Apache-2.0); some upstream templates derive from heygen-com/hyperframes (Apache-2.0). Keep notices in scripts/ and assets/templates/. -->

写若干个单文件 HTML 动画场景，本机渲染成一个 MP4。HTML 即视频：能用 CSS/JS 表达的画面都能变成片子。

## 工作流

### Step 1 · 需求澄清

问清（或基于内容合理默认并说明）：

1. **内容来源**：主题 / 文章 / 文字稿（视频链接先走 mandarinai-video-fetch 取文字稿）
2. **时长与场景数**：默认 3-5 个场景、总长 15-30 秒；单场景片头 5 秒左右
3. **风格**：从模板目录挑（见 Step 2），或按内容推荐
4. **比例**：默认 1920x1080（16:9）；竖屏 1080x1920 需在场景 HTML 里同步改版式

### Step 2 · 挑场景模板

读 `references/templates.md` 选型。六个内置模板（`assets/templates/`）：

| 模板 | 风格 | 适合 |
|------|------|------|
| `glitch-title.html` | 故障艺术 / cyberpunk | 片头、转场、"system online" |
| `liquid-hero.html` | 极光流体渐变 | 产品亮相、大声明 |
| `light-leak-cinema.html` | 暖调胶片漏光 | 情绪片段、品牌片、年度回顾 |
| `data-chart-nyt.html` | 报纸风动画折线图 | "数字涨了"的故事 |
| `text-cursor.html` | 终端打字机 | 代码 / CLI 演示、逐字揭示 |
| `logo-outro.html` | 干净 logo 收尾 | 任何片子的结尾页 |

每个场景：**拷贝模板 → 替换为真实内容 → 保持视觉签名**。不要 lorem ipsum，不要占位图。写新场景或大改动画前必读 `references/authoring.md`（时长探测规则、字体、循环动画的写法都在里面）。

用 `logo-outro.html` 时必须把品牌资产拷到场景同目录（模板按相对路径引用）：

```bash
cp <SKILL_ROOT>/assets/brand/mandarinai-icon.png <场景目录>/   # 宽字标版本：mandarinai-logo.png
```

### Step 3 · 渲染

```bash
cd <SKILL_ROOT>
node scripts/render.mjs -o ~/Downloads/out.mp4 scene1.html scene2.html scene3.html
```

- 多个场景自动按顺序拼接；`-d 5` 强制每场景精确 5 秒（不足时定格补齐），默认 `auto` 按动画实际长度
- `-s 1080x1920` 竖屏；`-f 60` 高帧率
- 依赖：本目录 `npm install && npx playwright install chromium`，以及 `ffmpeg`（`brew install ffmpeg`）
- 模板用了 Tailwind CDN 和 Google Fonts，渲染机器需要网络；字体加载有 8 秒上限兜底

### Step 4 · 验证

1. `ffprobe -v error -show_entries format=duration,size -of default=nw=1 out.mp4` 确认时长量级正确
2. 在浏览器里打开每个场景 HTML 过一遍：文字没溢出、动画在预期时长内走完
3. 总时长明显不对（如 5 秒默认值），通常是动画全写成了 `infinite`——读 `references/authoring.md` 的探测规则
4. **交付诚实**：交付说明/README 里的时长、分辨率、编码只能来自对真实文件的 `ffprobe` 读数。没有渲出 MP4 时，交付第一句必须说明"未渲染成 MP4"，并给出用户本地渲染的确切命令——**绝不描述不存在的产物**

## 运行环境适配

按当前环境的实际能力选渲染路径，降级必须声明，不许悄悄跳过：

- **(a) Node + Playwright + ffmpeg**（Claude Code / Codex CLI / Gemini CLI 本机）：走上面的主工作流 `render.mjs`。
- **(b) 无浏览器但有 ffmpeg**（ChatGPT / Codex 云沙箱）：`render.mjs` 跑不了，但仍要交出真实 MP4——用环境的原生图像生成能力（沿用 mandarinai-illustration 的能力阶梯）按分镜生成场景静帧，**不要用 PIL/matplotlib 手绘场景**，再用 ffmpeg 拼片：每帧 `zoompan` 缓推成小段，`concat` 拼接，`subtitles` 烧字幕，音轨合流：

  ```bash
  ffmpeg -loop 1 -t 6 -i s01.png -vf "zoompan=z='1+0.04*on/(30*6)':d=30*6:s=1920x1080,fps=30" -pix_fmt yuv420p s01.mp4
  ffmpeg -f concat -safe 0 -i list.txt -i ambient.wav -vf "subtitles=subs.srt" -c:v libx264 -c:a aac -shortest out.mp4
  ```

  渲完同样过 Step 4 验证（含 ffprobe）。
- **(c) 两条路都没有**：交付"渲染工程包"——场景 HTML + 场景清单 + 用户本地渲染的确切命令，并按 Step 4 的交付诚实规则明说没有渲出 MP4。
- 场景 HTML 放在用户项目或输出目录里，不要写进 skill 目录。

## 约束

- **品牌 logo 只能合成 `assets/brand/` 里的资产文件**，任何环境、任何渲染路径下都不得手绘/重绘/用形状拼凑
- 输出 MP4 无音轨；需要配音/配乐时提示用户可以用 ffmpeg 合流（`-i video.mp4 -i audio.m4a -c:v copy -shortest`）
- 不做长视频剪辑、不处理真人素材；取网络视频文字稿用 mandarinai-video-fetch
- auto 探测的单场景上限 30 秒（`-d` 显式指定最长 120 秒），更长的内容拆场景
