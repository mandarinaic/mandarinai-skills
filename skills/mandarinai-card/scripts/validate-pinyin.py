#!/usr/bin/env python3
"""Validate a filled poem/pinyin card HTML before capture.

Enforces the rules in references/pinyin-annotation.md that are mechanically
checkable, so the model only has to get the *content* right (which reading a
polyphone takes, whether a gloss is faithful) instead of also policing markup.

  python3 scripts/validate-pinyin.py /tmp/mandarinai_cast_poem_jingyesi.html

Errors (exit 1) — the card is wrong and must be fixed before capture:
  - unfilled {{PLACEHOLDER}} left in the file
  - a Hanzi inside .hanzi with no <ruby> annotation
  - a <ruby> whose base is not exactly one Hanzi (punctuation swept inside)
  - an <rt> holding zero or more than one syllable (whole-line pinyin in one rt)
  - uppercase pinyin, tone numbers (chuang2), or v standing in for ü
  - a .line with no .gloss translation
  - estimated line width over the 860px content box

Warnings (exit 0) — worth a look, not fatal:
  - a syllable with no tone mark that is not a common neutral-tone particle
  - more than one 朱砂 .shu highlight on a card
  - more than 4 .line blocks (mode-poem.md says split into several cards)
  - line-end punctuation not using .punct-hang
  - a gloss long enough to wrap past two lines
"""

import argparse
import re
import sys
import unicodedata
from html.parser import HTMLParser
from pathlib import Path

MAX_LINE_PX = 860        # 1036 card - 2x88 stage padding
WIDTH_FACTOR = 1.28      # per mode-poem.md's width estimate
MAX_LINES = 4            # per card
MAX_GLOSS_CHARS = 90     # ~2 lines at the template's gloss sizes
PLACEHOLDER_RE = re.compile(r"\{\{[A-Z_]+\}\}")
HANZI_FONT_RE = re.compile(r"\.hanzi\s*\{[^}]*?font-size:\s*(\d+(?:\.\d+)?)px", re.S)
TONE_MARKS = set("āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜńňǹḿ")
# particles that are correctly written toneless
NEUTRAL_OK = {"de", "le", "ma", "me", "men", "ne", "ba", "a", "ya", "wa", "la",
              "zi", "tou", "zhe", "ge", "shang", "lai", "qu"}

errors, warnings = [], []


def err(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


def is_hanzi(ch):
    cp = ord(ch)
    return (0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF
            or 0xF900 <= cp <= 0xFAFF or cp == 0x3007)


def has_tone_mark(syl):
    return any(c in TONE_MARKS for c in unicodedata.normalize("NFC", syl))


def check_syllable(syl, where):
    raw = syl.strip()
    if not raw:
        err(f"{where}: empty <rt> — every Hanzi needs a pinyin syllable")
        return
    if len(raw.split()) > 1:
        err(f"{where}: <rt> holds {len(raw.split())} syllables ({raw!r}) — "
            "one <ruby> per Hanzi, one syllable per <rt>")
        return
    if any(c.isdigit() for c in raw):
        err(f"{where}: tone number in {raw!r} — use tone marks (chuáng, not chuang2)")
        return
    if raw != raw.lower():
        err(f"{where}: pinyin must be all lowercase, got {raw!r}")
        return
    if "v" in raw:
        err(f"{where}: v standing in for ü in {raw!r} — write nǚ, not nv")
        return
    if not has_tone_mark(raw) and raw not in NEUTRAL_OK:
        warn(f"{where}: {raw!r} carries no tone mark — intended as neutral tone?")


class CardParser(HTMLParser):
    """Collects .line blocks: their ruby units, punctuation, and gloss."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lines = []          # [{"units": int, "gloss": str|None, "no": int}]
        self.stack = []          # (tag, classes)
        self.cur = None
        self.ruby_base = None    # accumulating text inside <ruby>, outside <rt>
        self.rt_text = None
        self.shu_count = 0
        self.tail = []           # trailing punctuation classes of the current line

    def _classes(self, attrs):
        return set(dict(attrs).get("class", "").split())

    def _in(self, name):
        return any(name in cls for _, cls in self.stack)

    def handle_starttag(self, tag, attrs):
        cls = self._classes(attrs)
        self.stack.append((tag, cls))
        if "line" in cls:
            self.cur = {"units": 0, "gloss": None, "no": len(self.lines) + 1,
                        "hanzi_seen": False}
            self.tail = []
        elif "shu" in cls:
            self.shu_count += 1
        elif tag == "ruby":
            self.ruby_base = ""
        elif tag == "rt":
            self.rt_text = ""

    def handle_endtag(self, tag):
        if tag == "rt" and self.rt_text is not None:
            where = f"line {self.cur['no'] if self.cur else '?'}"
            check_syllable(self.rt_text, where)
            self.rt_text = None
        elif tag == "ruby" and self.ruby_base is not None:
            base = self.ruby_base.strip()
            no = self.cur["no"] if self.cur else "?"
            hz = [c for c in base if is_hanzi(c)]
            if len(base) != 1 or not hz:
                err(f"line {no}: <ruby> base is {base!r} — it must be exactly one "
                    "Hanzi; punctuation goes outside the <ruby>")
            if self.cur is not None:
                self.cur["units"] += 1
                self.cur["hanzi_seen"] = True
            self.ruby_base = None
            self.tail = []
        if self.stack:
            popped_tag, cls = self.stack.pop()
            if "line" in cls and self.cur is not None:
                self.lines.append(self.cur)
                self.cur = None

    def handle_data(self, data):
        if self.rt_text is not None:
            self.rt_text += data
            return
        if self.ruby_base is not None:
            self.ruby_base += data
            return
        if self.cur is None:
            return
        if self._in("gloss"):
            self.cur["gloss"] = (self.cur["gloss"] or "") + data
            return
        if self._in("hanzi"):
            text = data.strip()
            if not text:
                return
            stray = [c for c in text if is_hanzi(c)]
            if stray:
                err(f"line {self.cur['no']}: Hanzi {''.join(stray)!r} has no "
                    "<ruby> annotation")
                self.cur["units"] += len(stray)
            punct = [c for c in text if not is_hanzi(c) and not c.isspace()]
            if punct:
                classes = set()
                for _, cls in self.stack:
                    classes |= cls
                if "punct-hang" not in classes:
                    self.cur["units"] += len(punct)
                    self.tail = list(punct)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("html", type=Path, help="filled poem card HTML")
    args = ap.parse_args()

    try:
        source = args.html.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"validate-pinyin failed: not found: {args.html}", file=sys.stderr)
        return 1

    for ph in sorted(set(PLACEHOLDER_RE.findall(source))):
        err(f"unfilled placeholder {ph}")

    parser = CardParser()
    parser.feed(source)

    if not parser.lines:
        err("no .line blocks found — is this a filled poem_template.html?")

    m = HANZI_FONT_RE.search(source)
    hanzi_px = float(m.group(1)) if m else None
    if hanzi_px is None:
        warn("could not read .hanzi font-size — skipping line-width check")

    for line in parser.lines:
        no = line["no"]
        gloss = (line["gloss"] or "").strip()
        if not gloss:
            err(f"line {no}: no .gloss translation — every line carries one")
        elif len(gloss) > MAX_GLOSS_CHARS:
            warn(f"line {no}: gloss is {len(gloss)} chars — over ~{MAX_GLOSS_CHARS} "
                 "wraps past two lines; tighten it")
        if not line["hanzi_seen"]:
            err(f"line {no}: no annotated Hanzi")
        if hanzi_px and line["units"]:
            width = line["units"] * hanzi_px * WIDTH_FACTOR
            if width > MAX_LINE_PX:
                err(f"line {no}: ~{width:.0f}px wide ({line['units']} units x "
                    f"{hanzi_px:.0f}px) — over the {MAX_LINE_PX}px box; drop a "
                    "size tier or switch to 联句 line breaking")

    if parser.tail:
        warn("line-end punctuation is not wrapped in .punct-hang — the Hanzi "
             "block will sit optically off-centre")
    if parser.shu_count > 1:
        warn(f"{parser.shu_count} .shu highlights — mode-poem.md allows at most 1")
    if len(parser.lines) > MAX_LINES:
        warn(f"{len(parser.lines)} lines on one card — over {MAX_LINES}; split "
             "into several cards with _1 / _2 suffixes")

    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    for e in errors:
        print(f"error: {e}", file=sys.stderr)
    if errors:
        print(f"\nvalidate-pinyin: {len(errors)} error(s) — fix before capture.",
              file=sys.stderr)
        return 1
    print(f"OK: {len(parser.lines)} line(s), "
          f"{len(warnings)} warning(s) — {args.html}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
