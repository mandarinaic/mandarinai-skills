#!/usr/bin/env python3
"""Export HSK words from the goose dev database into the skill's static bundle.

Usage: python3 export-bundle.py [out.json.gz]
       (default: ../assets/hsk-cards-v1.json.gz relative to this script)

Requires the goose dev Postgres running in docker (container pgvector-dev,
db x_mandarin). Re-run whenever the dictionary is enriched.

Bundle shape per word:
  { "id", "word", "trad", "pinyin", "zhuyin", "pos", "level", "en",
    "audio", "examples": [ { "zh", "pinyin", "en" } ] }
"""

import gzip
import json
import subprocess
import sys
from pathlib import Path

SQL = r"""
SELECT COALESCE(json_agg(row_to_json(t)), '[]'::json) FROM (
  SELECT
    w.id,
    w.word,
    NULLIF(w.word_t, '')   AS trad,
    w.pinyin,
    NULLIF(w.zhuyin, '')   AS zhuyin,
    NULLIF(w.part_of_speech, '') AS pos,
    w.hsk_level            AS level,
    NULLIF(w.english, '')  AS en,
    NULLIF(w.audio, '')    AS audio,
    (
      SELECT COALESCE(json_agg(json_build_object(
        'zh', e.chinese_text,
        'pinyin', e.pinyin_text,
        'en', (
          SELECT et.translated_text FROM c_hsk_example_translation et
          WHERE et.example_id = e.id AND et.language IN ('en','en-US')
          ORDER BY et.id LIMIT 1
        )
      ) ORDER BY e.example_order), '[]'::json)
      FROM (
        SELECT * FROM c_hsk_word_example e2
        WHERE e2.word_id = w.id
        ORDER BY e2.example_order LIMIT 3
      ) e
    ) AS examples
  FROM c_hsk_word w
  WHERE w.word <> ''
  ORDER BY w.hsk_level, w.id
) t;
"""


def main():
    default_out = Path(__file__).resolve().parent.parent / "assets" / "hsk-cards-v1.json.gz"
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_out

    proc = subprocess.run(
        ["docker", "exec", "pgvector-dev", "psql", "-U", "postgres", "-d", "x_mandarin",
         "-t", "-A", "-c", SQL],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        sys.exit(f"psql failed: {proc.stderr[-800:]}")

    words = json.loads(proc.stdout)
    # Strip null fields to keep the bundle small.
    for w in words:
        for k in [k for k, v in list(w.items()) if v is None]:
            del w[k]
        for ex in w.get("examples", []):
            for k in [k for k, v in list(ex.items()) if v is None]:
                del ex[k]

    bundle = {
        "version": 1,
        "source": "goose x_mandarin c_hsk_word",
        "tts_url_template": "https://api.wohuimandarin.com/nls/tts?text={urlencoded_text}",
        "levels": sorted({w["level"] for w in words}),
        "count": len(words),
        "words": words,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(out_path, "wt", encoding="utf-8") as f:
        json.dump(bundle, f, ensure_ascii=False, separators=(",", ":"))
    size = out_path.stat().st_size
    print(f"OK: {out_path} ({len(words)} words, {size // 1024} KB gz)")


if __name__ == "__main__":
    main()
