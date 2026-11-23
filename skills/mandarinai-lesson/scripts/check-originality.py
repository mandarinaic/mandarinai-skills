#!/usr/bin/env python3
"""Fail a lesson package that reproduces text from a private reference corpus.

The corpus is a directory of transcribed reference pages (``**/pages/*.md``) that we use
for syllabus mapping only. Package text must be original. Short stock phrases (你好,
谢谢, 多少钱) are expected to match and are not counted. This catches:

* any run of >= RUN Chinese characters that also occurs in the corpus (hard fail), and
* package lines of >= LINE characters identical to a corpus line. Too many such lines,
  or two in a row, means a dialogue was transcribed rather than written (fail).

Usage:
  python3 check-originality.py lesson.json --corpus ~/workspace/chinese/textbook-source
Exit status 0 = pass, 1 = fail, 2 = usage error. Standard library only.
"""
import argparse
import json
import re
import sys
from pathlib import Path

RUN = 10           # characters in a copied run that fails outright
LINE = 6           # minimum characters for a whole-line match to count
LINE_SHARE = 0.20  # fail when more than this share of checked lines match
CJK = re.compile(r"[㐀-䶿一-鿿]")


def cjk_only(text):
    return "".join(CJK.findall(text))


def corpus(root):
    pages = sorted(Path(root).expanduser().glob("**/pages/*.md"))
    if not pages:
        sys.exit(f"error: no **/pages/*.md files under {root}")
    joined, lines = [], set()
    for page in pages:
        body = page.read_text(encoding="utf-8")
        joined.append(cjk_only(body))
        for line in body.splitlines():
            # dialogue lines often carry a speaker label: 小叶：今天星期三。
            text = cjk_only(re.sub(r"^[^：:]{1,8}[：:]", "", line))
            if len(text) >= LINE:
                lines.add(text)
    return "\n".join(joined), lines


def package_lines(pkg):
    """(where, text) for every learner-facing Chinese string in the package."""
    for turn in pkg.get("dialogue", []):
        yield f"dialogue {turn.get('id')}", turn.get("zh", "")
    for pat in pkg.get("patterns", []):
        for key in ("pattern", "example", "example_zh"):
            if isinstance(pat.get(key), str):
                yield f"pattern {pat.get('id')}", pat[key]
        for ex in pat.get("examples", []) or []:
            yield f"pattern {pat.get('id')}", ex.get("zh", "") if isinstance(ex, dict) else str(ex)
    for q in pkg.get("questions", []):
        qid = q.get("id")
        for locale_text in (q.get("prompt") or {}).values():
            yield f"question {qid} prompt", locale_text
        for opt in q.get("options", []) or []:
            yield f"question {qid} option", opt.get("text", "")
        for chunk in q.get("chunks", []) or []:
            yield f"question {qid} chunks", chunk.get("text", "")
        for accepted in (q.get("answer") or {}).get("accepted", []) or []:
            yield f"question {qid} accepted", accepted


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("lesson")
    ap.add_argument("--corpus", required=True, help="directory containing **/pages/*.md")
    args = ap.parse_args()
    try:
        pkg = json.loads(Path(args.lesson).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: cannot read {args.lesson}: {exc}", file=sys.stderr)
        return 2
    text, book_lines = corpus(args.corpus)

    failures, line_hits, checked = [], [], 0
    previous_hit = False
    for where, raw in package_lines(pkg):
        s = cjk_only(raw)
        for i in range(len(s) - RUN + 1):
            if s[i:i + RUN] in text:
                failures.append(f"{where}: copied run {s[i:i + RUN]}")
                break
        if len(s) >= LINE:
            checked += 1
            hit = s in book_lines
            if hit:
                line_hits.append(f"{where}: {raw}")
                if previous_hit and where.startswith("dialogue"):
                    failures.append(f"{where}: second consecutive dialogue line identical to the corpus")
            previous_hit = hit and where.startswith("dialogue")

    share = len(line_hits) / checked if checked else 0.0
    if share > LINE_SHARE:
        failures.append(f"{len(line_hits)}/{checked} lines identical to corpus lines ({share:.0%} > {LINE_SHARE:.0%})")

    for hit in line_hits:
        print(f"note  identical line: {hit}")
    for failure in failures:
        print(f"FAIL  {failure}")
    print(f"{'FAIL' if failures else 'PASS'}: {checked} lines checked, {len(line_hits)} identical, "
          f"{len(failures)} failures")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
