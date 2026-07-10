# 发布到公众号（可选 · Path B · Chrome CDP）

**可选**功能。写作是本 skill 的本体；这一步只是把写好的 Markdown 灌进公众号编辑器，省掉手动复制粘贴。不需要 AppID / AppSecret，不需要服务号认证，**个人订阅号也能用**——因为它走的是你已登录的浏览器，不是 API。

为什么不用官方 API：草稿/发布 API 只对**认证服务号**开放，且要求**IP 白名单**，个人订阅号根本拿不到权限。所以这里走浏览器自动化。

## 分工

| 谁 | 做什么 | 为什么 |
|----|--------|--------|
| **你（人）** | ① 带远程调试启动 Chrome ② 登录 mp.weixin.qq.com（扫码）③ 新建文章打开编辑器 | 登录、扫码、过验证——脚本碰不了 |
| **脚本** | 连上那个编辑器标签页，填标题/作者，把正文粘进去，留成草稿 | 机械、易错的体力活 |

脚本**永远不发表**。它只填草稿，配图和「发表」由你在浏览器里手动完成。

## 步骤

### 1. 装依赖（一次性）

```bash
cd skills/mandarinai-wechat && npm install
```

（只需 `playwright` 的 JS 包即可连接已有 Chrome；不必 `playwright install chromium`，因为用的是你自己的 Chrome。）

### 2. 带远程调试启动 Chrome

用一个独立的 user-data-dir，别动你日常的 Chrome：

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/.wechat-chrome"
```

### 3. 登录并打开编辑器

在这个 Chrome 里：

1. 打开 https://mp.weixin.qq.com ，扫码登录
2. **新的创作 → 文章**，让编辑器（有标题框 + 正文区）停在前台

### 4. 跑脚本

```bash
node scripts/publish-wechat.mjs ~/Documents/notes/20260617-标题关键词.md --port 9222
# 想顺手点「保存为草稿」：加 --save-draft
```

脚本会：找到编辑器标签页 → 填标题/作者 → 把正文作为一次粘贴事件灌进去（ProseMirror/UEditor 都吃 paste）→ 截图存到 skill 目录方便核对。

### 5. 你来收尾

回到 Chrome：**手动设封面**、在 `配图` 占位处插入图片（封面交 `mandarinai-social-card`，文中长图交 `mandarinai-card`），核对排版，点**发表**。

> **封面/配图为什么不自动传？** 公众号页面上唯一暴露的通用文件 `<input>` 会把图片插进**正文**，不是封面位；封面走的是微信自己的素材库弹层，脚本点不动。所以脚本只灌文字、留草稿，图片和封面一律人工。别让脚本去碰上传——实测它只会把封面图误插进正文。

> **新版编辑器的坑（已处理）**：新版公众号把**标题也做成了 ProseMirror**，页面上有两个 `.ProseMirror`（第一个是标题、第二个才是正文）。早期脚本用裸 `.ProseMirror` 会把整篇正文灌进标题、触发 `3016/64`（标题超长）。现在脚本在页面内自动区分：标题取 `#title`/第一个可编辑区，正文取 `.rich_media_content` 里的那个，正文先灌、标题后填，并把标题截到 64 字以内。

## 只要 HTML、不要自动化？

不想开浏览器，只想要一段能直接粘进编辑器的带样式 HTML：

```bash
node scripts/md-to-wechat-html.mjs article.md -o article.html
```

公众号编辑器会保留内联样式（class 和 `<style>` 会被剥掉，所以脚本把样式全内联了）。打开 `article.html`、全选复制、粘进编辑器即可。

## 排障

- **连不上**：确认第 2 步的 Chrome 还开着，端口对得上（默认 9222）。
- **找不到编辑器标签页**：确认第 3 步的文章编辑器在那个被调试的 Chrome 里、且已打开（不是另一个普通 Chrome 窗口）。
- **标题/正文没进去**：公众号 DOM 会变。脚本会打印它解析到的 `title:` / `body:` 节点和页面可编辑区数量；若 `title` 和 `body` 解析成了同一个节点，会有 `⚠` 警告——这时先看截图，再到 `scripts/publish-wechat.mjs` 的 `resolveEditorInPage()` 里调整正文优先选择器（默认 `.rich_media_content` 内的可编辑区）。
- **标题被填进正文 / 正文跑到标题**：见上「新版编辑器的坑」。脚本现在正文先灌、标题后填、按 `#title` 与 `.rich_media_content` 区分，已规避；若微信再次改版，对照 `resolveEditorInPage()` 更新。
