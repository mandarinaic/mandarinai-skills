#!/usr/bin/env node
// Generate illustrations via OpenAI GPT-Image or Google Gemini image APIs.
// Zero dependencies (Node 18+ native fetch).
//
// Env (any subset works; missing providers are skipped in auto mode):
//   OPENAI_API_KEY      OpenAI key (image model access requires verified org)
//   OPENAI_BASE_URL     optional custom endpoint, default https://api.openai.com/v1
//   OPENAI_IMAGE_MODEL  optional model override, default gpt-image-1
//   GEMINI_API_KEY      Google AI Studio key (GOOGLE_API_KEY also accepted)
//   GEMINI_BASE_URL     optional custom endpoint, default https://generativelanguage.googleapis.com
//   GEMINI_IMAGE_MODEL  optional model override, default gemini-2.5-flash-image
//
// Usage:
//   node generate-image.mjs --prompt "..." [options]
//   node generate-image.mjs --prompt-file prompt.txt [options]
//
// Options:
//   --provider auto|openai|gemini   default auto (openai → gemini)
//   --ratio R       1.9:1 (default) | 16:9 | 21:9 | 4:3 | 3:2 | 1:1 | 3:4 | 9:16 | 2:3
//   --count N       images to generate (default 1)
//   --out DIR       output directory (default ./assets)
//   --name BASE     purpose-based file basename, e.g. agent-loop (default: illustration)
//   --model M       model override for the chosen provider (beats env override)
//   --ref FILE      reference image for character/style consistency (repeatable);
//                   OpenAI switches to the images/edits endpoint, Gemini passes
//                   the image(s) inline before the prompt
//
// Every image appends a record (file, provider/model, ratio, full prompt) to
// <out>/PROMPTS.md so the set can be reproduced.

import { mkdirSync, appendFileSync, writeFileSync, readFileSync } from "node:fs";
import { join } from "node:path";

function parseArgs(argv) {
  const args = { provider: "auto", ratio: "1.9:1", count: 1, out: "assets", name: "illustration", ref: [] };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--ref") args.ref.push(argv[++i]);
    else if (a.startsWith("--")) args[a.slice(2)] = argv[++i];
  }
  args.count = Number(args.count) || 1;
  return args;
}

function refMime(path) {
  const p = path.toLowerCase();
  return p.endsWith(".jpg") || p.endsWith(".jpeg") ? "image/jpeg"
    : p.endsWith(".webp") ? "image/webp"
    : "image/png";
}

const KEYS = {
  openai: process.env.OPENAI_API_KEY,
  gemini: process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY,
};

const BASES = {
  openai: (process.env.OPENAI_BASE_URL || "https://api.openai.com/v1").replace(/\/+$/, ""),
  gemini: (process.env.GEMINI_BASE_URL || "https://generativelanguage.googleapis.com").replace(/\/+$/, ""),
};

const DEFAULT_MODELS = {
  openai: process.env.OPENAI_IMAGE_MODEL || "gpt-image-1",
  gemini: process.env.GEMINI_IMAGE_MODEL || "gemini-2.5-flash-image",
};

// OpenAI image models only accept three fixed sizes; map any ratio to the nearest.
function openaiSize(ratio) {
  const [w, h] = ratio.split(":").map(Number);
  if (!w || !h || w === h) return "1024x1024";
  return w > h ? "1536x1024" : "1024x1536";
}

// Gemini accepts named aspect ratios; map unsupported ones to the closest match.
const GEMINI_RATIOS = new Set(["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"]);
function geminiRatio(ratio) {
  if (GEMINI_RATIOS.has(ratio)) return ratio;
  const [w, h] = ratio.split(":").map(Number);
  if (!w || !h) return "16:9";
  const r = w / h;
  let best = "16:9", bestDiff = Infinity;
  for (const cand of GEMINI_RATIOS) {
    const [cw, ch] = cand.split(":").map(Number);
    const diff = Math.abs(cw / ch - r);
    if (diff < bestDiff) { bestDiff = diff; best = cand; }
  }
  return best;
}

async function generateOpenai(prompt, ratio, count, model, refs) {
  let res;
  if (refs.length) {
    // Reference images require the edits endpoint (multipart form).
    const form = new FormData();
    form.append("model", model);
    form.append("prompt", prompt);
    form.append("size", openaiSize(ratio));
    form.append("n", String(count));
    for (const ref of refs) {
      const buf = readFileSync(ref);
      form.append("image[]", new Blob([buf], { type: refMime(ref) }), ref.split("/").pop());
    }
    res = await fetch(`${BASES.openai}/images/edits`, {
      method: "POST",
      headers: { Authorization: `Bearer ${KEYS.openai}` },
      body: form,
    });
  } else {
    res = await fetch(`${BASES.openai}/images/generations`, {
      method: "POST",
      headers: { Authorization: `Bearer ${KEYS.openai}`, "Content-Type": "application/json" },
      body: JSON.stringify({ model, prompt, size: openaiSize(ratio), n: count }),
    });
  }
  if (!res.ok) throw new Error(`openai HTTP ${res.status}: ${(await res.text()).slice(0, 300)}`);
  const data = await res.json();
  return (data.data || []).map((d) => ({ b64: d.b64_json, mime: "image/png" }));
}

async function generateGemini(prompt, ratio, count, model, refs) {
  const refParts = refs.map((ref) => ({
    inlineData: { mimeType: refMime(ref), data: readFileSync(ref).toString("base64") },
  }));
  const images = [];
  for (let i = 0; i < count; i++) {
    const res = await fetch(`${BASES.gemini}/v1beta/models/${model}:generateContent`, {
      method: "POST",
      headers: { "x-goog-api-key": KEYS.gemini, "Content-Type": "application/json" },
      body: JSON.stringify({
        contents: [{ parts: [...refParts, { text: prompt }] }],
        generationConfig: {
          responseModalities: ["TEXT", "IMAGE"],
          imageConfig: { aspectRatio: geminiRatio(ratio) },
        },
      }),
    });
    if (!res.ok) throw new Error(`gemini HTTP ${res.status}: ${(await res.text()).slice(0, 300)}`);
    const data = await res.json();
    const parts = data.candidates?.[0]?.content?.parts || [];
    const img = parts.find((p) => p.inlineData?.data);
    if (!img) throw new Error(`gemini returned no image (finishReason: ${data.candidates?.[0]?.finishReason || "unknown"})`);
    images.push({ b64: img.inlineData.data, mime: img.inlineData.mimeType || "image/png" });
  }
  return images;
}

const PROVIDERS = { openai: generateOpenai, gemini: generateGemini };

function extFor(mime) {
  return mime.includes("jpeg") ? ".jpg" : mime.includes("webp") ? ".webp" : ".png";
}

async function main() {
  const args = parseArgs(process.argv);
  const prompt = args.prompt || (args["prompt-file"] ? readFileSync(args["prompt-file"], "utf8").trim() : "");
  if (!prompt) {
    console.error('Usage: node generate-image.mjs --prompt "<text>" | --prompt-file FILE [--provider auto|openai|gemini] [--ratio 1.9:1] [--count N] [--out DIR] [--name BASE] [--model M] [--ref IMAGE ...]');
    process.exit(1);
  }

  const order = args.provider === "auto" ? ["openai", "gemini"] : [args.provider];
  if (args.provider !== "auto" && !PROVIDERS[args.provider]) {
    console.error(`Unknown provider: ${args.provider}`);
    process.exit(1);
  }

  let images = [];
  let used = null;
  let model = null;
  const skipped = [];

  for (const name of order) {
    if (!KEYS[name]) {
      skipped.push(`${name} (no ${name === "gemini" ? "GEMINI_API_KEY" : "OPENAI_API_KEY"})`);
      continue;
    }
    model = args.model || DEFAULT_MODELS[name];
    try {
      images = await PROVIDERS[name](prompt, args.ratio, args.count, model, args.ref);
      if (images.length) { used = name; break; }
      skipped.push(`${name} (no image returned)`);
    } catch (e) {
      skipped.push(`${name} (${e.message})`);
    }
  }

  if (!used) {
    console.error(`Generation failed. Tried: ${skipped.join("; ") || order.join(", ")}`);
    process.exit(2);
  }

  mkdirSync(args.out, { recursive: true });
  const results = [];
  for (let i = 0; i < images.length; i++) {
    const img = images[i];
    const file = images.length > 1 ? `${args.name}-${i + 1}${extFor(img.mime)}` : `${args.name}${extFor(img.mime)}`;
    const filePath = join(args.out, file);
    writeFileSync(filePath, Buffer.from(img.b64, "base64"));
    appendFileSync(
      join(args.out, "PROMPTS.md"),
      `## ${file}\n\n- provider: ${used} / ${model}\n- ratio: ${args.ratio}\n${args.ref.length ? `- refs: ${args.ref.join(", ")}\n` : ""}\n\`\`\`text\n${prompt}\n\`\`\`\n\n`
    );
    results.push({ file: filePath, provider: used, model, ratio: args.ratio });
  }
  if (skipped.length) console.error(`note: skipped ${skipped.join("; ")}`);
  console.log(JSON.stringify({ provider: used, model, generated: results }, null, 2));
}

main().catch((e) => {
  console.error(e.message || e);
  process.exit(1);
});
