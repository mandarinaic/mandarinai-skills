# 可选特效库 · 影院级 Hero 页处理（风格 A 专用）

<!-- attribution: recipes extracted from nexu-io/html-video templates (Apache-2.0), some upstream from heygen-com/hyperframes (Apache-2.0). -->

从视频帧模板生态提炼的 6 个 CSS 特效配方，用于给**风格 A 电子杂志风**的 hero 页（封面 / 幕封 / 收尾）做一次性视觉强化。

## 使用纪律（先读这个）

- **只用于 hero 页**，正文页保持模板原样——克制优于炫技
- **一份 deck 最多选 1 个特效家族**，从头用到尾（封面用了 glitch，收尾也用 glitch 或不用，不许中途换 cinema）
- **风格 B 瑞士风全部禁用**——渐变 / 颗粒 / 模糊都违反瑞士风硬规则
- 特效作为 `<section>` 内的覆盖层 div 或 body-level 伪元素加在 hero 页内,不要改模板全局 CSS
- 同一套配方在 mandarinai-video skill 里是完整视频模板;deck 与配套视频可共用一个视觉家族

## 1. 胶片颗粒（Film Grain）

最百搭、最不抢戏。叠在任何 hero 页上立刻有"印刷物/胶片"质感：

```html
<div style="position:absolute; inset:0; opacity:.12; mix-blend-mode:overlay; pointer-events:none; z-index:6;
  background-image:url(&quot;data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='240' height='240'%3E%3Cfilter id='n'%3E%3CfeTurbulence baseFrequency='0.85' numOctaves='2'/%3E%3C/filter%3E%3Crect width='240' height='240' filter='url(%23n)'/%3E%3C/svg%3E&quot;)"></div>
```

搭配主题：🍂 牛皮纸 / 🌙 沙丘 / 🖋 墨水经典。

## 2. 暖调漏光（Light Leak）

胶片感的暖橙光斑，适合人文 / 回顾主题的封面或收尾页：

```html
<div style="position:absolute; inset:0; pointer-events:none; z-index:1; opacity:.5;
  background:radial-gradient(ellipse at 78% 18%, rgba(255,181,71,.55) 0%, transparent 38%),
             radial-gradient(ellipse at 90% 30%, rgba(255,126,63,.4) 0%, transparent 30%)"></div>
```

配套：暗角 `radial-gradient(circle at center, transparent 50%, rgba(0,0,0,.6) 100%)` + 颗粒（配方 1）。
搭配主题：🍂 牛皮纸 / 🌙 沙丘。漏光位置可改 ellipse 坐标，放在标题对角。

## 3. 极光流体色斑（Liquid Aurora）

大色斑 + 大模糊 + screen 混合，缓慢漂浮。比 WebGL 背景更"湿"，适合 AI / 创意主题封面：

```html
<style>
  @keyframes blob-f1 { 0%,100% { transform:translate(0,0) scale(1) } 50% { transform:translate(80px,-60px) scale(1.15) } }
</style>
<div style="position:absolute; width:600px; height:600px; border-radius:50%; mix-blend-mode:screen;
  filter:blur(70px); background:#a78bfa; top:-100px; left:-100px; opacity:.5;
  animation:blob-f1 12s ease-in-out infinite; pointer-events:none"></div>
```

2-4 个色斑，同族亮色（紫 #a78bfa / 粉 #ec4899 / 青 #06b6d4），各自不同的 keyframes 与时长。
注意：与模板自带 WebGL 背景二选一（hero 页 section 局部覆盖即可），不要叠加。

## 4. 故障像散（Glitch / Chromatic Offset）

cyan/magenta 双层错位 + 间歇抖动。只适合科技 / 安全 / "system" 类主题，全 deck 最多一处（封面大标题）：

```html
<style>
  @keyframes glitch { 0%,92%,100%{transform:translate(0,0)} 93%{transform:translate(-6px,1px)} 94%{transform:translate(8px,-2px)} 96%{transform:translate(4px,-1px)} }
  .fx-glitch{position:relative; animation:glitch 4s infinite}
  .fx-glitch .layer{position:absolute; inset:0; mix-blend-mode:screen}
</style>
<h1 class="h-hero fx-glitch">SIGNAL
  <span class="layer" style="color:#00f0ff; transform:translate(-3px,1px)" aria-hidden="true">SIGNAL</span>
  <span class="layer" style="color:#ff2bd6; transform:translate(3px,-1px)" aria-hidden="true">SIGNAL</span>
</h1>
```

配套扫描线：`repeating-linear-gradient(0deg, rgba(0,0,0,.18) 0 1px, transparent 1px 3px)` 覆盖层。
英文短词效果最好；中文标题慎用（笔画密，错位糊成一团）。

## 5. CRT 扫描线（Scanlines）

比 glitch 轻量的科技感，可单独用：

```html
<div style="position:absolute; inset:0; pointer-events:none; z-index:5; opacity:.5; mix-blend-mode:multiply;
  background-image:repeating-linear-gradient(0deg, rgba(0,0,0,.18) 0px, rgba(0,0,0,.18) 1px, transparent 1px, transparent 3px)"></div>
```

## 6. 打字机标题（Typewriter Reveal）

逐字打出 + 方块光标，适合开发者向 deck 的封面副标（不要用在主标题，翻页动效会打架）：

```html
<style>
  @keyframes caret { 0%,49%{opacity:1} 50%,100%{opacity:0} }
</style>
<p class="lead" style="font-family:var(--mono)">
  <span id="tw"></span><span style="display:inline-block; width:.55em; height:1.1em; background:currentColor; vertical-align:-.15em; animation:caret 1s step-end infinite"></span>
</p>
<script>
  (function(){ const t='$ deck --start'; let i=0; const el=document.getElementById('tw');
    (function tick(){ if(i<=t.length){ el.textContent=t.slice(0,i++); setTimeout(tick,70);} })(); })();
</script>
```

## 想要完整的视频版？

这些配方的完整动画版（含渲染到 MP4）在 **mandarinai-video** skill：deck 用静态特效，配套宣传片用同一视觉家族的视频模板，视觉上是一套。
