#!/usr/bin/env node
// Fetch stock photos from Pexels / Unsplash / Pixabay via their official APIs.
// Zero dependencies (Node 18+ native fetch).
//
// Env keys (any subset works; missing providers are skipped in auto mode):
//   PEXELS_API_KEY    https://www.pexels.com/api/
//   UNSPLSH_API_KEY   https://unsplash.com/developers  (UNSPLASH_API_KEY also accepted)
//   PIXABAY_API_KEY   https://pixabay.com/api/docs/
//
// Usage:
//   node fetch-stock-image.mjs --query "mountain sunrise" [options]
//
// Options:
//   --provider auto|pexels|unsplash|pixabay   default auto (pexels → unsplash → pixabay)
//   --orientation landscape|portrait|square   default landscape
//   --count N       images to download (default 1)
//   --index N       start at the Nth search result (default 0)
//   --out DIR       output directory (default ./assets)
//   --name BASE     purpose-based file basename, e.g. hero-mountain (default: slug of query)
//   --list          print candidates as JSON, download nothing
//
// Every download appends a provenance line to <out>/SOURCES.md:
//   <file> ← <page url> (photo by <author>, via <provider>)

import { mkdirSync, appendFileSync, writeFileSync } from "node:fs";
import { join, extname } from "node:path";

function parseArgs(argv) {
  const args = { provider: "auto", orientation: "landscape", count: 1, index: 0, out: "assets", list: false };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--list") args.list = true;
    else if (a.startsWith("--")) args[a.slice(2)] = argv[++i];
  }
  args.count = Number(args.count) || 1;
  args.index = Number(args.index) || 0;
  return args;
}

const KEYS = {
  pexels: process.env.PEXELS_API_KEY,
  unsplash: process.env.UNSPLSH_API_KEY || process.env.UNSPLASH_API_KEY,
  pixabay: process.env.PIXABAY_API_KEY,
};

async function searchPexels(query, orientation, perPage) {
  const u = new URL("https://api.pexels.com/v1/search");
  u.searchParams.set("query", query);
  u.searchParams.set("per_page", String(perPage));
  u.searchParams.set("orientation", orientation); // landscape|portrait|square
  const res = await fetch(u, { headers: { Authorization: KEYS.pexels } });
  if (!res.ok) throw new Error(`pexels HTTP ${res.status}`);
  const data = await res.json();
  return (data.photos || []).map((p) => ({
    provider: "pexels",
    downloadUrl: p.src?.large2x || p.src?.original,
    pageUrl: p.url,
    author: p.photographer,
    width: p.width,
    height: p.height,
    alt: p.alt || "",
  }));
}

async function searchUnsplash(query, orientation, perPage) {
  const u = new URL("https://api.unsplash.com/search/photos");
  u.searchParams.set("query", query);
  u.searchParams.set("per_page", String(perPage));
  u.searchParams.set("orientation", orientation === "square" ? "squarish" : orientation);
  const res = await fetch(u, { headers: { Authorization: `Client-ID ${KEYS.unsplash}` } });
  if (!res.ok) throw new Error(`unsplash HTTP ${res.status}`);
  const data = await res.json();
  return (data.results || []).map((p) => ({
    provider: "unsplash",
    downloadUrl: p.urls?.raw ? `${p.urls.raw}&w=2400&q=85&fm=jpg` : p.urls?.full,
    pageUrl: p.links?.html,
    author: p.user?.name,
    width: p.width,
    height: p.height,
    alt: p.alt_description || "",
    // Unsplash API guidelines require pinging this when the photo is used.
    trackUrl: p.links?.download_location,
  }));
}

async function searchPixabay(query, orientation, perPage) {
  const u = new URL("https://pixabay.com/api/");
  u.searchParams.set("key", KEYS.pixabay);
  u.searchParams.set("q", query);
  u.searchParams.set("image_type", "photo");
  u.searchParams.set("per_page", String(Math.max(perPage, 3))); // pixabay minimum is 3
  if (orientation === "landscape") u.searchParams.set("orientation", "horizontal");
  if (orientation === "portrait") u.searchParams.set("orientation", "vertical");
  const res = await fetch(u);
  if (!res.ok) throw new Error(`pixabay HTTP ${res.status}`);
  const data = await res.json();
  return (data.hits || []).map((p) => ({
    provider: "pixabay",
    downloadUrl: p.fullHDURL || p.largeImageURL,
    pageUrl: p.pageURL,
    author: p.user,
    width: p.imageWidth,
    height: p.imageHeight,
    alt: p.tags || "",
  }));
}

const PROVIDERS = { pexels: searchPexels, unsplash: searchUnsplash, pixabay: searchPixabay };

function slug(s) {
  return s.toLowerCase().replace(/[^a-z0-9一-鿿]+/g, "-").replace(/^-|-$/g, "").slice(0, 40) || "photo";
}

async function download(photo, filePath) {
  const res = await fetch(photo.downloadUrl);
  if (!res.ok) throw new Error(`download HTTP ${res.status} for ${photo.downloadUrl}`);
  writeFileSync(filePath, Buffer.from(await res.arrayBuffer()));
  if (photo.trackUrl && KEYS.unsplash) {
    fetch(photo.trackUrl, { headers: { Authorization: `Client-ID ${KEYS.unsplash}` } }).catch(() => {});
  }
}

async function main() {
  const args = parseArgs(process.argv);
  if (!args.query) {
    console.error('Usage: node fetch-stock-image.mjs --query "<keyword>" [--provider auto|pexels|unsplash|pixabay] [--orientation landscape|portrait|square] [--count N] [--index N] [--out DIR] [--name BASE] [--list]');
    process.exit(1);
  }

  const order = args.provider === "auto" ? ["pexels", "unsplash", "pixabay"] : [args.provider];
  if (args.provider !== "auto" && !PROVIDERS[args.provider]) {
    console.error(`Unknown provider: ${args.provider}`);
    process.exit(1);
  }

  const need = args.index + args.count;
  const perPage = Math.min(Math.max(need + 4, 10), 30);
  let photos = [];
  let used = null;
  const skipped = [];

  for (const name of order) {
    if (!KEYS[name]) {
      skipped.push(`${name} (no ${name === "unsplash" ? "UNSPLSH_API_KEY" : name.toUpperCase() + "_API_KEY"})`);
      continue;
    }
    try {
      const found = await PROVIDERS[name](args.query, args.orientation, perPage);
      if (found.length > args.index) {
        photos = found;
        used = name;
        break;
      }
      skipped.push(`${name} (no results)`);
    } catch (e) {
      skipped.push(`${name} (${e.message})`);
    }
  }

  if (!used) {
    console.error(`No results for "${args.query}". Tried: ${skipped.join(", ") || order.join(", ")}`);
    process.exit(2);
  }

  const picked = photos.slice(args.index, args.index + args.count);

  if (args.list) {
    console.log(JSON.stringify({ provider: used, query: args.query, candidates: photos }, null, 2));
    return;
  }

  mkdirSync(args.out, { recursive: true });
  const base = args.name || slug(args.query);
  const results = [];
  for (let i = 0; i < picked.length; i++) {
    const p = picked[i];
    const ext = (extname(new URL(p.downloadUrl).pathname) || ".jpg").split("?")[0] || ".jpg";
    const file = picked.length > 1 ? `${base}-${i + 1}${ext}` : `${base}${ext}`;
    const filePath = join(args.out, file);
    await download(p, filePath);
    appendFileSync(join(args.out, "SOURCES.md"), `- ${file} ← ${p.pageUrl} (photo by ${p.author}, via ${p.provider})\n`);
    results.push({ file: filePath, pageUrl: p.pageUrl, author: p.author, provider: p.provider, width: p.width, height: p.height, alt: p.alt });
  }
  if (skipped.length) console.error(`note: skipped ${skipped.join(", ")}`);
  console.log(JSON.stringify({ provider: used, downloaded: results }, null, 2));
}

main().catch((e) => {
  console.error(e.message || e);
  process.exit(1);
});
