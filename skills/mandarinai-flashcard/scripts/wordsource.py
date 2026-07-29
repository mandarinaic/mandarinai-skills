"""Word source for mandarinai-flashcard: live MandarinAi API first, bundle fallback.

Canonical card shape (the /api/flashcards/hsk response item):
  { id, word, word_t?, pinyin, zhuyin?, part_of_speech?, hsk_level, meaning,
    image?, audio?, examples: [ { chinese, pinyin?, translation? } ] }

Env:
  MANDARIN_API_BASE  default https://www.mandarinai.com
"""

import gzip
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

API_BASE = os.environ.get("MANDARIN_API_BASE", "https://www.mandarinai.com")
BUNDLE = Path(__file__).resolve().parent.parent / "assets" / "hsk-cards-v1.json.gz"
UA = "Mozilla/5.0 (mandarinai-flashcard skill)"
WORD_URL = "https://www.mandarinai.com/hsk/word/detail/{id}"


def _api_get(path, params):
    url = f"{API_BASE}{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        payload = json.loads(r.read().decode("utf-8"))
    if payload.get("code") != 200:
        raise RuntimeError(f"api code {payload.get('code')}: {str(payload)[:200]}")
    return payload["data"]


def _from_api(level, words, count, offset, language):
    if words:
        cards = []
        for i in range(0, len(words), 50):
            chunk = words[i:i + 50]
            data = _api_get("/api/flashcards/hsk",
                            {"words": ",".join(chunk), "language": language})
            cards += data.get("list") or []
        return cards
    cards, need = [], offset + count
    page, page_size = 1, min(100, max(20, need))
    while len(cards) < need:
        data = _api_get("/api/flashcards/hsk",
                        {"level": level or "", "page": page,
                         "page_size": page_size, "language": language})
        batch = data.get("list") or []
        cards += batch
        if len(batch) < page_size:
            break
        page += 1
    return cards[offset:offset + count]


def _from_bundle(level, words, count, offset, language):
    with gzip.open(BUNDLE, "rt", encoding="utf-8") as f:
        all_words = json.load(f)["words"]

    def normalize(w):
        return {
            "id": w["id"], "word": w["word"], "word_t": w.get("trad", ""),
            "pinyin": w.get("pinyin", ""), "zhuyin": w.get("zhuyin", ""),
            "part_of_speech": w.get("pos", ""), "hsk_level": w.get("level", 0),
            "meaning": w.get("en", ""), "audio": w.get("audio", ""),
            "examples": [{"chinese": e.get("zh", ""), "pinyin": e.get("pinyin", ""),
                          "translation": e.get("en", "")} for e in w.get("examples", [])],
        }

    if words:
        index = {}
        for w in all_words:
            index.setdefault(w["word"], w)
        return [normalize(index[t]) for t in words if t in index]
    pool = [w for w in all_words if not level or w.get("level") == level]
    return [normalize(w) for w in pool[offset:offset + count]]


def get_words(level=0, words=None, count=20, offset=0, language="en", source="auto"):
    """Returns (cards, source_used). source: auto | api | bundle."""
    if source in ("auto", "api"):
        try:
            cards = _from_api(level, words, count, offset, language)
            return cards, "api"
        except Exception as e:
            if source == "api":
                raise
            print(f"warning: live API unavailable ({e}); using offline bundle "
                  f"(data may be stale — fresh data lives at mandarinai.com)", file=sys.stderr)
    if language != "en":
        print("warning: offline bundle only carries English meanings", file=sys.stderr)
    return _from_bundle(level, words, count, offset, language), "bundle"


def report_missing(requested, cards):
    got = {c["word"] for c in cards}
    return [w for w in requested or [] if w not in got]
