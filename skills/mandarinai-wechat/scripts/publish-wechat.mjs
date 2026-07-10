#!/usr/bin/env node
/*
 * publish-wechat.mjs — fill an already-open WeChat 公众号 article editor with
 * this skill's Markdown, via Chrome DevTools Protocol (no API keys).
 *
 * Division of labor (the human does the fragile parts, the script the tedious):
 *   YOU:    1. launch Chrome with remote debugging:
 *              "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
 *                --remote-debugging-port=9222 --user-data-dir="$HOME/.wechat-chrome"
 *           2. log into https://mp.weixin.qq.com (scan QR)
 *           3. open a new article editor: 新的创作 → 文章
 *   SCRIPT: connect, find that editor tab, set title/author, paste the body,
 *           leave it as a draft for you to review images + publish.
 *
 *   node publish-wechat.mjs <article.md> [--port 9222] [--save-draft]
 *
 * --save-draft  attempt to click 保存为草稿 after filling (off by default —
 *               the script never publishes; you click 发表 yourself).
 *
 * Best-effort: WeChat's editor DOM drifts. The script tries several selectors,
 * logs what it matched, and screenshots the result so you can verify.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";
import { mdToWechatHtml } from "./md-to-wechat-html.mjs";

const args = process.argv.slice(2);
let file = null, port = 9222, saveDraft = false;
for (let i = 0; i < args.length; i++) {
  if (args[i] === "--port") port = +args[++i];
  else if (args[i] === "--save-draft") saveDraft = true;
  else if (!file) file = args[i];
}
if (!file) { console.error("usage: node publish-wechat.mjs <article.md> [--port 9222] [--save-draft]"); process.exit(1); }

const { html, title, author } = mdToWechatHtml(fs.readFileSync(file, "utf8"));
const here = path.dirname(fileURLToPath(import.meta.url));

const TITLE_MAX = 64; // WeChat rejects longer titles (error 3016/64)

// Resolve title/body/author IN-PAGE and tag them, because the new WeChat editor
// makes BOTH the title and the body `.ProseMirror` — a bare ".ProseMirror" grabs
// the TITLE, which is how the whole article used to land in the title field.
// Title is the FIRST editable / #title; body is a DIFFERENT editable, preferring
// the one inside .rich_media_content, else the tallest. Returns what it tagged.
function resolveEditorInPage() {
  const q = (s) => document.querySelector(s);
  const editables = [...document.querySelectorAll('.ProseMirror,[contenteditable="true"]')];
  const titleEl = q("#title") || q("textarea[placeholder*='标题'],input[placeholder*='标题']") || editables[0] || null;
  const bodies = editables.filter((el) => el !== titleEl && !(titleEl && titleEl.contains(el)) && !el.closest("#title"));
  const bodyEl = bodies.find((el) => el.closest(".rich_media_content"))
    || bodies.sort((a, b) => b.scrollHeight - a.scrollHeight)[0]
    || q("#ueditor_0") || null;
  const authorEl = q("#author") || q("input[placeholder*='作者']");
  if (titleEl) titleEl.setAttribute("data-xh", "title");
  if (bodyEl) bodyEl.setAttribute("data-xh", "body");
  if (authorEl) authorEl.setAttribute("data-xh", "author");
  const tag = (el) => (el ? (el.id ? "#" + el.id : el.tagName.toLowerCase() + "." + (el.className || "").split(" ")[0]) : null);
  return { title: tag(titleEl), body: tag(bodyEl), author: !!authorEl, editables: editables.length };
}

// contenteditable-aware setter (the new title is a ProseMirror, not an <input>)
async function setTagged(page, which, value) {
  return page.evaluate(({ w, v }) => {
    const el = document.querySelector(`[data-xh="${w}"]`);
    if (!el) return false;
    el.focus();
    if (el.tagName === "INPUT" || el.tagName === "TEXTAREA") {
      const setter = Object.getOwnPropertyDescriptor(el.__proto__, "value")?.set;
      setter ? setter.call(el, v) : (el.value = v);
    } else {
      el.textContent = v; // contenteditable / ProseMirror
    }
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  }, { w: which, v: value });
}

async function main() {
  let browser;
  try {
    browser = await chromium.connectOverCDP(`http://127.0.0.1:${port}`);
  } catch (e) {
    console.error(`✗ Could not connect to Chrome on port ${port}.`);
    console.error(`  Launch Chrome first:`);
    console.error(`  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --remote-debugging-port=${port} --user-data-dir="$HOME/.wechat-chrome"`);
    process.exit(2);
  }

  // find the editor tab and resolve+tag title/body/author in one pass
  const pages = [];
  for (const ctx of browser.contexts()) pages.push(...ctx.pages());
  let page = null, resolved = null;
  for (const p of pages) {
    try {
      const r = await p.evaluate(`(${resolveEditorInPage.toString()})()`);
      if (r && r.body) { page = p; resolved = r; break; }
    } catch { /* page not evaluable (chrome:// etc.) */ }
  }

  if (!page) {
    console.error("✗ No WeChat article editor (body region) found among open tabs.");
    console.error("  In your debugged Chrome: log into mp.weixin.qq.com, then 新的创作 → 文章,");
    console.error("  so the editor (title + body) is open. Then re-run.");
    process.exit(3);
  }
  console.error(`✓ Found editor tab: ${page.url()}`);
  console.error(`  resolved → title: ${resolved.title}  body: ${resolved.body}  (editables on page: ${resolved.editables})`);
  if (resolved.title && resolved.body && resolved.title === resolved.body)
    console.error("  ⚠ title and body resolved to the same node — check the screenshot before trusting this run");

  // body FIRST (so a mis-resolve can't dump the article into the title), then title/author
  const plain = html.replace(/<[^>]+>/g, "");
  const pasted = await page.evaluate(({ h, t }) => {
    const el = document.querySelector('[data-xh="body"]');
    if (!el) return "no body node";
    el.focus();
    try {
      const dt = new DataTransfer();
      dt.setData("text/html", h);
      dt.setData("text/plain", t);
      el.dispatchEvent(new ClipboardEvent("paste", { clipboardData: dt, bubbles: true, cancelable: true }));
      return true;
    } catch (e) { return String(e); }
  }, { h: html, t: plain });
  console.error(pasted === true ? "✓ body pasted into body editor" : `⚠ body paste failed: ${pasted} — paste the HTML manually`);

  if (title) {
    let t = title;
    if (t.length > TITLE_MAX) { t = t.slice(0, TITLE_MAX); console.error(`  ⚠ title truncated to ${TITLE_MAX} chars (WeChat limit)`); }
    const ok = await setTagged(page, "title", t);
    console.error(ok ? `✓ title set: ${t}` : `⚠ title field not found — set it manually`);
  }
  if (author) {
    const ok = await setTagged(page, "author", author);
    console.error(ok ? `✓ author set: ${author}` : `⚠ author field not found — set it manually`);
  }

  await page.waitForTimeout(1500);

  if (saveDraft) {
    const clicked = await page.evaluate(() => {
      const btn = [...document.querySelectorAll("a,button,span")].find((b) => /保存为草稿|保存草稿/.test(b.textContent || ""));
      if (btn) { btn.click(); return btn.textContent.trim(); }
      return null;
    });
    console.error(clicked ? `✓ clicked: ${clicked}` : "⚠ 保存为草稿 button not found — save manually");
    await page.waitForTimeout(1500);
  }

  const shot = path.join(here, "..", `wechat-editor-${Date.now()}.png`);
  try { await page.screenshot({ path: shot, fullPage: false }); console.error(`✓ screenshot: ${shot}`); } catch {}

  console.error("\nNext: review the draft in Chrome — set the 封面 and insert 配图 images by hand, then click 发表 yourself.");
  console.error("Images/cover are NOT automated on purpose: WeChat's only generic file <input> drops images into the BODY,");
  console.error("not the 封面 slot, and the cover uses WeChat's own 素材库 dialog. Pick those manually. (This script never publishes.)");

  // connectOverCDP: do NOT close — leave the user's Chrome running
  browser.contexts(); // keep ref
  process.exit(0);
}

main().catch((e) => { console.error("✗ " + (e?.stack || e)); process.exit(1); });
