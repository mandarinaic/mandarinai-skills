# 平台差异与排错

## YouTube

- 几乎都有自动字幕；`fetch-video.sh` 默认语言序列 `zh.*,zh-Hans,zh-CN,en.*,en` 通常直接命中。
- 年龄限制 / 会员视频：加 `-c chrome`。
- 自动字幕是滚动式的，重复行多——脚本已做去重，但清洗步骤仍要合并半句。

## bilibili（B站）

- yt-dlp 原生支持 BV 号页面与 `b23.tv` 短链（脚本会先展开短链）。
- 人工 CC 字幕可直接拿；**AI 字幕必须登录**，加 `-c chrome` 用浏览器 cookies。
- 没有任何字幕时走音频转写。多 P 视频默认只取链接指向的那一 P（`--no-playlist`）。

## 小红书（xiaohongshu）

- 支持 `www.xiaohongshu.com/explore/...` 笔记页和 `xhslink.com` 分享短链（脚本自动展开）。
- 笔记视频**没有字幕**，必走音频 + whisper 转写；通常需要 `-c chrome`（登录 cookies），否则元数据都拿不到。
- 图文笔记不是视频：正文文字直接用网页抓取，不要走本 skill。

## 抖音 / 其他

- yt-dlp 支持的平台都能走同一脚本；先直接试，再按报错加 cookies。
- 查 yt-dlp 是否支持某平台：`yt-dlp --list-extractors | grep -i <名字>`。

## 转写工具选择（无字幕时）

| 优先级 | 工具 | 配置 | 说明 |
|--------|------|------|------|
| 1 | 远程 whisper 服务器 | `WHISPER_BASE_URL` + 可选 `WHISPER_API_KEY` | 自建 whisper_server.py（faster-whisper large-v3 on GPU），API：`POST /transcribe`（multipart 上传）→ 轮询 `GET /status/{job_id}`，Bearer 认证 |
| 2 | mlx-whisper | `pip install mlx-whisper` | Apple Silicon 本地最快，默认 small 模型够用 |
| 3 | openai-whisper | `pip install openai-whisper` | 通用但慢；中文建议 `--model medium` |

远程服务器健康检查：`curl $WHISPER_BASE_URL/health`。报 401/403 说明 `WHISPER_API_KEY` 缺失或不对。

长视频（>30 分钟）转写前先告知用户预计耗时，确认再跑。

## 常见错误

| 现象 | 处理 |
|------|------|
| `could not read video metadata` | 加 `-c chrome`；确认链接在浏览器里能打开 |
| 字幕乱码/语言不对 | 用 `-l` 指定语言，如 `-l "ja.*,ja"` |
| yt-dlp 报 extractor 错误 | `brew upgrade yt-dlp`（平台改版后旧版常失效） |
| cookies 读取失败（Chrome 锁库） | 先完全退出 Chrome 再跑，或改用 `-c safari` |
