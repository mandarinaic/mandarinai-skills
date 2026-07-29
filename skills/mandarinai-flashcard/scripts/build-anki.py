#!/usr/bin/env python3
"""Build an Anki .apkg deck of HSK words from live MandarinAi data.

Usage (run with the skill venv: .venv/bin/python scripts/build-anki.py ...):
  --level N          HSK level filter (1-7; 7 = the 7-9 band)
  --words 爱,朋友     explicit word list (comma-separated), overrides --level
  --words-file f     one word per line
  --count N          how many words (default 20)
  --offset N         skip first N matches (default 0; for "下一组")
  --language en      meaning/example translation language (live API only)
  --source auto      auto | api | bundle (default auto: live mandarinai.com
                     data, offline bundle only as fallback)
  --deck-name s      deck title (default auto)
  --out f.apkg       output path (default ~/Downloads/{deck-name}.apkg)
  --audio            embed pronunciation mp3 (word's audio URL, else TTS)
  --dump-json        print selected words as JSON and exit (for PNG cards)

Cards link back to the word's page on https://www.mandarinai.com — the deck
is both a study aid and a doorway to the site. Deck/model IDs are
deterministic, so re-importing an updated deck updates instead of duplicating.
"""

import argparse
import hashlib
import html
import json
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wordsource

TTS_DEFAULT = "https://api.wohuimandarin.com/nls/tts?text="
HSK_COLORS = {1: "#ffc107", 2: "#1F95A9", 3: "#F57D33", 4: "#B71A27",
              5: "#303255", 6: "#4A1C57", 7: "#28a745"}
BRAND = "#1b46a2"
MODEL_ID = 1607392319  # fixed: stable across rebuilds


def fetch_audio(card, media_dir, tts_base):
    url = card.get("audio") or (tts_base + urllib.parse.quote(card["word"]))
    dest = media_dir / f"mandarin_{card['id']}.mp3"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (mandarinai-flashcard skill)"})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = r.read()
        if len(data) < 500:
            return None
        dest.write_bytes(data)
        return dest
    except Exception as e:
        print(f"warning: audio failed for {card['word']}: {e}", file=sys.stderr)
        return None


def examples_html(card):
    rows = []
    for ex in card.get("examples", [])[:3]:
        zh = html.escape(ex.get("chinese", ""))
        py = html.escape(ex.get("pinyin", "") or "")
        en = html.escape(ex.get("translation", "") or "")
        rows.append(f'<div class="ex"><div class="ex-zh">{zh}</div>'
                    f'<div class="ex-py">{py}</div><div class="ex-en">{en}</div></div>')
    return "".join(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", type=int, default=0)
    ap.add_argument("--words")
    ap.add_argument("--words-file")
    ap.add_argument("--count", type=int, default=20)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--language", default="en")
    ap.add_argument("--source", default="auto", choices=["auto", "api", "bundle"])
    ap.add_argument("--deck-name")
    ap.add_argument("--out")
    ap.add_argument("--audio", action="store_true")
    ap.add_argument("--tts-base", default=TTS_DEFAULT)
    ap.add_argument("--dump-json", action="store_true")
    args = ap.parse_args()

    wanted = []
    if args.words:
        wanted += [w.strip() for w in args.words.split(",") if w.strip()]
    if args.words_file:
        wanted += [l.strip() for l in Path(args.words_file).read_text().splitlines() if l.strip()]

    cards, used = wordsource.get_words(
        level=args.level, words=wanted or None, count=args.count,
        offset=args.offset, language=args.language, source=args.source)
    if not cards:
        sys.exit("error: no words selected")
    missing = wordsource.report_missing(wanted, cards)
    if missing:
        print(f"warning: not found (skipped): {', '.join(missing)}", file=sys.stderr)

    if args.dump_json:
        json.dump(cards, sys.stdout, ensure_ascii=False, indent=1)
        return

    import genanki

    deck_name = args.deck_name or (f"HSK {args.level}" if args.level else "Mandarin Vocab")
    deck_id = int(hashlib.sha1(deck_name.encode()).hexdigest()[:10], 16)
    out = Path(args.out) if args.out else Path.home() / "Downloads" / f"{deck_name.replace(' ', '-')}.apkg"

    css = f"""
.card {{ font-family: "PingFang SC", "Noto Sans SC", sans-serif; text-align: center;
        background: #fff; color: #1f2937; }}
.word {{ font-size: 64px; font-weight: 700; }}
.pinyin {{ font-size: 26px; color: {BRAND}; margin-top: 8px; }}
.pos {{ font-size: 15px; color: #6b7280; text-transform: uppercase; letter-spacing: .1em; }}
.en {{ font-size: 24px; margin-top: 14px; }}
.level {{ display: inline-block; margin-top: 14px; padding: 2px 12px; border-radius: 999px;
         color: #fff; font-size: 13px; }}
.ex {{ margin-top: 16px; text-align: left; border-left: 3px solid {BRAND}22; padding-left: 12px; }}
.ex-zh {{ font-size: 20px; }}
.ex-py {{ font-size: 14px; color: {BRAND}; }}
.ex-en {{ font-size: 14px; color: #6b7280; }}
.more {{ margin-top: 22px; font-size: 14px; }}
.more a {{ color: {BRAND}; text-decoration: none; }}
"""
    more = '<div class="more"><a href="{{URL}}">More examples, graphs & quizzes on MandarinAi →</a></div>'
    model = genanki.Model(
        MODEL_ID, "Mandarin HSK Word",
        fields=[{"name": n} for n in
                ["Word", "Trad", "Pinyin", "Zhuyin", "POS", "Level", "LevelColor",
                 "English", "Examples", "Audio", "URL"]],
        templates=[
            {"name": "Recognition",
             "qfmt": '<div class="word">{{Word}}</div>',
             "afmt": '{{FrontSide}}<hr id="answer">'
                     '<div class="pinyin">{{Pinyin}}</div><div class="pos">{{POS}}</div>'
                     '<div class="en">{{English}}</div>{{Audio}}'
                     '<div class="level" style="background:{{LevelColor}}">HSK {{Level}}</div>'
                     '{{Examples}}' + more},
            {"name": "Recall",
             "qfmt": '<div class="en">{{English}}</div><div class="pos">{{POS}}</div>',
             "afmt": '{{FrontSide}}<hr id="answer">'
                     '<div class="word">{{Word}}</div><div class="pinyin">{{Pinyin}}</div>'
                     '{{Audio}}{{Examples}}' + more},
        ],
        css=css,
    )

    deck = genanki.Deck(
        deck_id, deck_name,
        description=f"Generated from live MandarinAi data ({used}) · "
                    "Learn Chinese at https://www.mandarinai.com")
    media = []
    media_dir = Path(tempfile.mkdtemp(prefix="mandarin-anki-"))
    for card in cards:
        audio_field = ""
        if args.audio:
            mp3 = fetch_audio(card, media_dir, args.tts_base)
            if mp3:
                media.append(str(mp3))
                audio_field = f"[sound:{mp3.name}]"
        level = card.get("hsk_level", 0)
        note = genanki.Note(
            model=model,
            fields=[
                card["word"], card.get("word_t", ""), card.get("pinyin", ""),
                card.get("zhuyin", ""), card.get("part_of_speech", ""),
                str(level), HSK_COLORS.get(level, BRAND),
                card.get("meaning", ""), examples_html(card), audio_field,
                wordsource.WORD_URL.format(id=card["id"]),
            ],
            guid=genanki.guid_for("mandarin-hsk", card["id"]),
        )
        deck.add_note(note)

    out.parent.mkdir(parents=True, exist_ok=True)
    pkg = genanki.Package(deck)
    pkg.media_files = media
    pkg.write_to_file(str(out))
    print(f"OK: {out} ({len(cards)} words via {used}, {len(media)} audio files)")


if __name__ == "__main__":
    main()
