---
name: mandarinai-video-fetch
description: "Fetch the transcript/text of an online video so downstream skills can turn it into articles, cards, or PPTs. Supports YouTube, bilibili (B站), xiaohongshu (小红书), douyin and other yt-dlp platforms — tries platform subtitles first, falls back to audio + whisper transcription. Use when the user gives a video link and wants 文字稿/字幕/转写/总结, or wants to 把视频做成文章/卡片/PPT (then chain into mandarinai-writes / mandarinai-card / mandarinai-ppt). Trigger words: '视频转文字', '拿字幕', 'transcript', 'B站视频', 'YouTube视频', '小红书视频', any video URL."
version: "0.1.0"
---

# mandarinai-video-fetch

把一条视频链接变成干净的文字稿。其他 skill（mandarinai-writes / mandarinai-card / mandarinai-ppt）拿到文字稿后再做内容生成。

## 工作流

### Step 1 · 取文字稿

从 skill 根目录运行：

```bash
bash scripts/fetch-video.sh "<视频URL>"
```

- 输出最后一行是 `TRANSCRIPT: <路径>`（成功）或 `AUDIO: <路径>`（无字幕且本机没有转写工具）。
- bilibili 的 AI 字幕、小红书、会员/登录内容需要浏览器 cookies：加 `-c chrome`（或 safari/firefox）。
- 平台差异和排错见 `references/platforms.md`。

依赖：`yt-dlp` + `ffmpeg`（必须，`brew install yt-dlp ffmpeg`）。无字幕视频的转写按优先级：

1. **远程 whisper 服务器**（推荐）：设置环境变量 `WHISPER_BASE_URL`（必需）和 `WHISPER_API_KEY`（服务器开了认证就要），脚本自动走远程转写，本机无需装任何模型。服务端是自建的 whisper_server.py（GPU 机器）。
2. 本地 `mlx_whisper` / `whisper`：环境变量缺失时回退（Apple Silicon 推荐 `pip install mlx-whisper`）。

环境变量未生效时提醒用户：env 要 export 给 CLI 进程（写进 `~/.zshrc` 或启动时传入），不是只在某个终端里设置过。

### Step 2 · 清洗

读取 TRANSCRIPT 文件后必须先清洗再使用：

1. 去掉口头水词（"嗯"、"啊"、"就是说"、"那个"、"like"、"you know"）。
2. 合并被字幕切碎的半句；恢复标点。
3. 自动字幕常见同音错字（人名、产品名、术语）按上下文修正，不确定的保留原文并标注 `[?]`。
4. 保留讲述顺序，不要按主题重排——下游 skill 自己决定结构。

### Step 3 · 交付或衔接

- 用户只要文字稿 → 把清洗后的文本存为 `{标题}.md` 交付（默认当前目录，或用户指定位置）。
- 用户要文章 / 卡片 / PPT → 把清洗后的文字稿作为输入,继续走 mandarinai-writes / mandarinai-card / mandarinai-ppt 的正常流程。

## 运行环境适配

- **Claude Code**：直接用 Bash 工具运行脚本。
- **Codex / Gemini CLI**：同样用 shell 执行；不要假设 Claude 专用工具存在。Gemini 首次激活会请求权限，属正常。

## 验证

- 文字稿非空、语言与视频一致、长度量级合理（10 分钟口播 ≈ 1500-3000 字）。
- 若内容明显是另一个视频（短链解析错误），报告并让用户确认链接。

## 约束

- 不做视频下载交付（只取音频做转写，用后即弃）；要下载视频本体的请求不属于本 skill。
- 不绕过平台付费/登录限制：cookies 只用于用户自己有权访问的内容。
