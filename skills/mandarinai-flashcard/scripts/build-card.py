#!/usr/bin/env python3
"""Build a 1080x1440 PNG vocab card from JSON card data.

The script owns the HTML structure rules so the model only supplies data:
assets/vocab_card.html is filled from a build-anki.py --dump-json card, with
the dictionary fields going in exactly as the API/bundle emitted them.

Poem / pinyin learning cards live in the mandarinai-card skill (`-p` mold),
which has the 和紙 template, the size-tier tables, and validate-pinyin.py.

Usage (plain python3 — no venv needed; PNG capture needs `npm install` once):
  python3 scripts/build-card.py CARD.json --png ~/Downloads/card.png
  python3 scripts/build-card.py DUMP.json --word 爱 --png ~/Downloads/爱.png

  CARD.json    card object with "type": "vocab" (see examples/vocab-ai.json),
               or a JSON array as printed by build-anki.py --dump-json
  --word W     select one word from a dump-array input (keeps dictionary data
               exactly as the source emitted it — never retype it)
  --html PATH  write the filled HTML here (default: a temp dir)
  --png PATH   screenshot via assets/capture.js (node + playwright)
  --force      overwrite existing outputs (default: refuse)
"""

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
HSK_COLORS = {1: "#ffc107", 2: "#1F95A9", 3: "#F57D33", 4: "#B71A27",
              5: "#303255", 6: "#4A1C57", 7: "#28a745"}
BRAND = "#1b46a2"
MAX_VOCAB_EXAMPLES = 2      # card face is 1080x1440, keep it breathable
MAX_MEANING_LEN = 70        # longer meanings are cut to the first sense
PLACEHOLDER_RE = re.compile(r"\{\{[A-Z_]+\}\}")


def fail(msg):
    raise SystemExit(f"build-card failed: {msg}")


def warn(msg):
    print(f"warning: {msg}", file=sys.stderr)


def read_template(name):
    path = SKILL_ROOT / "assets" / name
    if not path.is_file():
        fail(f"template not found: {path}")
    return path.read_text(encoding="utf-8")


def build_vocab(card):
    word = str(card.get("word", "")).strip()
    if not word:
        fail("vocab card needs a word")
    pinyin = str(card.get("pinyin", "")).strip()
    meaning = str(card.get("meaning", "")).strip()
    if not pinyin or not meaning:
        fail(f"{word}: vocab card needs pinyin and meaning — dictionary data "
             "from the API/bundle, never invented")
    if len(meaning) > MAX_MEANING_LEN:
        first = re.split(r"[;；]", meaning)[0].strip()
        if first and first != meaning:
            warn(f"{word}: meaning cut to first sense: {first}")
            meaning = first

    level = card.get("hsk_level") or 0
    chip = f"HSK {level}" if level else "Vocab"
    rows = []
    for ex in card.get("examples") or []:
        zh = str(ex.get("chinese", "")).strip()
        if not zh:
            continue
        py = html.escape(str(ex.get("pinyin", "") or ""))
        en = html.escape(str(ex.get("translation", "") or ""))
        rows.append(f'<div class="ex"><div class="ex-zh">{html.escape(zh)}</div>'
                    f'<div class="ex-py">{py}</div><div class="ex-en">{en}</div></div>')
        if len(rows) == MAX_VOCAB_EXAMPLES:
            break
    if not rows:
        warn(f"{word}: no examples on the card")

    # the chip text replaces the whole "HSK {{LEVEL}}" literal so non-HSK
    # words get a plain "Vocab" chip instead of "HSK Vocab"
    return (read_template("vocab_card.html")
            .replace("HSK {{LEVEL}}", html.escape(chip))
            .replace("{{LEVEL_COLOR}}", HSK_COLORS.get(level, BRAND))
            .replace("{{POS}}", html.escape(str(card.get("part_of_speech", "") or "")))
            .replace("{{WORD}}", html.escape(word))
            .replace("{{PINYIN}}", html.escape(pinyin))
            .replace("{{EN}}", html.escape(meaning))
            .replace("{{EXAMPLES_HTML}}", "".join(rows)))


def output_paths(args, slug):
    if args.html:
        html_path = Path(args.html).expanduser()
    else:
        html_path = Path(tempfile.mkdtemp(prefix="mandarin-card-")) / f"{slug}.html"
    png_path = Path(args.png).expanduser() if args.png else None
    for target in (html_path, png_path):
        if target and target.exists() and not args.force:
            fail(f"refusing to overwrite {target} — pick a new name or pass --force")
    return html_path, png_path


def capture(html_path, png_path):
    node = shutil.which("node")
    if not node:
        fail("node not found — PNG capture needs Node.js (or use --html only)")
    result = subprocess.run(
        [node, "assets/capture.js", str(html_path), str(png_path), "1080", "1440"],
        cwd=SKILL_ROOT)
    if result.returncode != 0:
        fail(f"capture.js failed for {html_path} — ran `npm install` in {SKILL_ROOT}?")


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", type=Path, help="card JSON or build-anki --dump-json array")
    ap.add_argument("--word", help="word to pick from a dump-array input")
    ap.add_argument("--html", help="output HTML path (default: temp dir)")
    ap.add_argument("--png", help="output PNG path (screenshots via capture.js)")
    ap.add_argument("--force", action="store_true", help="overwrite existing outputs")
    args = ap.parse_args()

    if not args.html and not args.png:
        fail("nothing to do: pass --png and/or --html")
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(f"input not found: {args.input}")
    except json.JSONDecodeError as e:
        fail(f"invalid JSON in {args.input}: {e}")

    if isinstance(data, list):
        if not data:
            fail(f"{args.input} is an empty array")
        if not args.word:
            words = ", ".join(str(c.get("word", "?")) for c in data[:20])
            fail(f"input is a dump array — pick one with --word (has: {words} …)")
        matches = [c for c in data if c.get("word") == args.word]
        if not matches:
            fail(f"word {args.word} not in dump ({len(data)} cards)")
        if len(matches) > 1:
            senses = " / ".join(str(c.get("meaning", "?")) for c in matches)
            warn(f"{args.word} has {len(matches)} entries ({senses}) — using the first")
        card = dict(matches[0])
        card["type"] = "vocab"
    else:
        card = data

    if card.get("type") == "poem":
        fail("poem cards moved to the mandarinai-card skill — use its -p mold "
             "(references/mode-poem.md), which owns the template and "
             "validate-pinyin.py")
    if card.get("type") != "vocab":
        fail('card JSON needs "type": "vocab" '
             "(or pass a --dump-json array plus --word)")

    page = build_vocab(card)
    slug = "".join(c if c.isalnum() else "-" for c in card["word"]).strip("-")[:40] or "card"
    html_path, png_path = output_paths(args, slug)

    # templates carry instructional HTML comments; keep them out of output
    page = re.sub(r"[ \t]*<!--.*?-->\n?", "", page, flags=re.S)
    leftover = sorted(set(PLACEHOLDER_RE.findall(page)))
    if leftover:
        fail(f"unfilled placeholders: {', '.join(leftover)}")
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(page, encoding="utf-8")
    if png_path:
        png_path.parent.mkdir(parents=True, exist_ok=True)
        capture(html_path, png_path)
    print(f"OK: {png_path or html_path}")


if __name__ == "__main__":
    main()
