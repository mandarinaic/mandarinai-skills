#!/usr/bin/env python3
"""Build a self-contained draft lesson preview, never overwriting an existing file."""
import argparse
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("lesson_validator", ROOT / "scripts/validate-lesson.py")
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def build(lesson_path, output):
    lesson = validator.load_lesson(lesson_path)
    template = (ROOT / "assets/preview.html").read_text(encoding="utf-8")
    payload = json.dumps(lesson, ensure_ascii=False).replace("<", "\\u003c").replace(
        ">", "\\u003e").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        stream.write(template.replace("__LESSON_JSON__", payload))
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lesson", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(build(args.lesson, args.out))
    except (ValueError, OSError) as error:
        parser.exit(1, f"Preview failed: {error}\n")


if __name__ == "__main__":
    main()
