#!/usr/bin/env python3
"""Build a HyperFrames project for a vertical Mandarin learning story video.

Input is a story JSON (see examples/story-example.json): a title plus one
scene per sentence — hanzi, per-Hanzi lowercase tone-marked pinyin, and a
translation. The script owns every structure rule:

  - ruby per Hanzi, punctuation outside ruby, pinyin forced lowercase,
    Hanzi/syllable count mismatches rejected (same rules as mandarinai-flashcard)
  - per-sentence TTS narration fetched from the MandarinAi TTS endpoint;
    scene timing derived from real audio duration (ffprobe)
  - GSAP timeline HTML generated from assets/story_page.html with karaoke
    per-character reveal, translation after the sentence is spoken, title and
    end cards with MandarinAi branding
  - refuses to overwrite an existing project dir (pass --force)

Usage:
  python3 scripts/build-video.py story.json --out ~/Documents/mandarin-videos/my-story
  python3 scripts/build-video.py story.json --out /tmp/story --no-audio   # silent, offline

Then render (commands are printed with real paths at the end):
  npx hyperframes check  <out> --json
  npx hyperframes render <out> --output <out>/renders/story-v1.mp4 --workers 1

Story JSON fields: title (required), scenes[] (required: hanzi / pinyin /
translation), level ("HSK 3", shown as a chip), subtitle, cta (end-card line),
lang (translation language code, default en), bgm (path to a licensed audio
file, mixed at bgm_volume, default 0.15), width/height (default 1080x1440),
composition_id (default mandarin-story).
"""

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
TTS_DEFAULT = "https://www.mandarinai.com/tts?text="
UA = "Mozilla/5.0 (mandarinai-story-video skill)"
MAX_SCENES = 20
LEAD = 0.9            # silence before narration while the sentence fades in
TITLE_DUR = 2.8
END_DUR = 3.2
MIN_SCENE_DUR = 3.5
NO_AUDIO_RATE = 0.42  # est. seconds per Hanzi for reveal pacing without TTS


def fail(msg):
    raise SystemExit(f"build-video failed: {msg}")


def warn(msg):
    print(f"warning: {msg}", file=sys.stderr)


# --- ruby building: same data rules as mandarinai-flashcard/scripts/build-card.py;
# the base char gets a span.b wrapper here so the karaoke tween can light up the
# character while its rt pinyin stays fully visible in every capture mode ---

def is_hanzi(ch):
    cp = ord(ch)
    return (0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF
            or 0xF900 <= cp <= 0xFAFF or cp == 0x3007)


def pinyin_syllables(raw, scene_no):
    if isinstance(raw, str):
        syllables = raw.split()
    elif isinstance(raw, list):
        syllables = [str(s).strip() for s in raw]
    else:
        fail(f"scene {scene_no}: pinyin must be a list (or one space-separated "
             "string) of per-Hanzi syllables")
    checked = []
    for syl in syllables:
        if not syl:
            fail(f"scene {scene_no}: empty pinyin syllable — every Hanzi needs pinyin")
        if any(c.isdigit() for c in syl):
            fail(f"scene {scene_no}: tone numbers not allowed ({syl}) — "
                 "use tone marks (chuáng, not chuang2)")
        if not all(c.isalpha() for c in syl):
            fail(f"scene {scene_no}: pinyin syllable has non-letter characters: {syl}")
        checked.append(syl.lower())
    return checked


def ruby_line(hanzi, pinyin, scene_no):
    syllables = pinyin_syllables(pinyin, scene_no)
    hanzi_count = sum(1 for ch in hanzi if is_hanzi(ch))
    if hanzi_count != len(syllables):
        fail(f"scene {scene_no} ({hanzi}): {hanzi_count} Hanzi but "
             f"{len(syllables)} pinyin syllables — one syllable per character")
    parts = []
    i = 0
    for ch in hanzi:
        if is_hanzi(ch):
            parts.append(f'<ruby><span class="b">{html.escape(ch)}</span>'
                         f"<rt>{html.escape(syllables[i])}</rt></ruby>")
            i += 1
        else:
            parts.append(f'<span class="punctuation">{html.escape(ch)}</span>')
    return "".join(parts)


# --- audio ---

def fetch_tts(text, dest, tts_base):
    url = tts_base + urllib.parse.quote(text)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
    except Exception as e:
        fail(f"TTS failed for「{text}」: {e} — fix the network or rerun with --no-audio")
    if len(data) < 500:
        fail(f"TTS returned no usable audio for「{text}」— rerun with --no-audio?")
    dest.write_bytes(data)


def audio_seconds(path):
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        fail("ffprobe not found — install ffmpeg (brew install ffmpeg) "
             "or rerun with --no-audio")
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except ValueError:
        fail(f"cannot read audio duration of {path}: {result.stderr.strip()}")


# --- story assembly ---

def read_time(translation):
    return min(max(1.2 + 0.03 * len(translation), 1.5), 3.0)


def resolve_scenes(story, out_dir, use_audio, tts_base):
    """Return (scenes_html, audio_html, timeline_scenes, total_duration)."""
    scenes = story.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        fail("story needs a non-empty scenes array")
    if len(scenes) > MAX_SCENES:
        fail(f"{len(scenes)} scenes > {MAX_SCENES} — split the story")
    if len(scenes) > 12:
        warn(f"{len(scenes)} scenes makes a long short — consider splitting")

    lang = str(story.get("lang", "")).strip() or "en"
    title = str(story.get("title", "")).strip()
    level = str(story.get("level", "")).strip()
    subtitle = str(story.get("subtitle", "")).strip()
    cta = str(story.get("cta", "")).strip() or "每天读一个小故事，轻松学中文。"

    sections, audio_tags, timeline = [], [], []
    cursor = 0.0

    chip = f'<span class="chip">{html.escape(level)}</span>\n      ' if level else ""
    sub = f'\n      <p class="story-sub">{html.escape(subtitle)}</p>' if subtitle else ""
    sections.append(
        f'    <section id="scene-title" class="scene clip" data-start="0" '
        f'data-duration="{TITLE_DUR:g}" data-track-index="1">\n'
        f'      <div class="center">\n      {chip}<h1 class="story-title">'
        f'{html.escape(title)}</h1>{sub}\n      </div>\n    </section>')
    timeline.append({"id": "scene-title", "start": 0, "dur": TITLE_DUR,
                     "revealAt": 0, "revealDur": 0, "transAt": 0})
    cursor += TITLE_DUR

    for no, scene in enumerate(scenes, 1):
        hanzi = str(scene.get("hanzi", "")).strip()
        if not hanzi:
            fail(f"scene {no}: missing hanzi")
        translation = str(scene.get("translation", "")).strip()
        if not translation:
            fail(f"scene {no} ({hanzi}): missing translation — every sentence needs one")
        if len(hanzi) > 24:
            warn(f"scene {no} has {len(hanzi)} characters — long for one screen; "
                 "consider splitting the sentence")
        ruby = ruby_line(hanzi, scene.get("pinyin"), no)
        scene_id = f"scene-{no:02d}"

        if use_audio:
            mp3 = out_dir / "assets" / "audio" / f"{scene_id}.mp3"
            fetch_tts(hanzi, mp3, tts_base)
            speak = audio_seconds(mp3)
            audio_tags.append(
                f'    <audio id="voice-{no:02d}" src="assets/audio/{scene_id}.mp3" '
                f'data-start="{cursor + LEAD:.2f}" data-duration="{speak:.2f}" '
                f'data-track-index="{40 + no}" data-volume="1"></audio>')
            reveal_dur = speak * 0.92
        else:
            speak = NO_AUDIO_RATE * sum(1 for c in hanzi if is_hanzi(c)) + 0.8
            reveal_dur = speak

        dur = max(LEAD + speak + 0.15 + read_time(translation), MIN_SCENE_DUR)
        trans_at = cursor + LEAD + speak + 0.15
        sections.append(
            f'    <section id="{scene_id}" class="scene clip" data-start="{cursor:.2f}" '
            f'data-duration="{dur:.2f}" data-track-index="{1 + no}">\n'
            f'      <div class="sentence">\n'
            f'        <p class="hanzi">{ruby}</p>\n'
            f'        <p class="translation" lang="{html.escape(lang)}">'
            f'{html.escape(translation)}</p>\n'
            f'      </div>\n    </section>')
        timeline.append({"id": scene_id, "start": round(cursor, 2), "dur": round(dur, 2),
                         "revealAt": round(cursor + LEAD, 2),
                         "revealDur": round(reveal_dur, 2),
                         "transAt": round(trans_at, 2)})
        cursor += dur

    sections.append(
        f'    <section id="scene-end" class="scene clip" data-start="{cursor:.2f}" '
        f'data-duration="{END_DUR:g}" data-track-index="{2 + len(scenes)}">\n'
        f'      <div class="center">\n'
        f'        <p class="end-cta">{html.escape(cta)}</p>\n'
        f'        <p class="end-brand">MandarinAi</p>\n'
        f'        <p class="end-site">mandarinai.com</p>\n'
        f'      </div>\n    </section>')
    timeline.append({"id": "scene-end", "start": round(cursor, 2), "dur": END_DUR,
                     "revealAt": 0, "revealDur": 0, "transAt": 0})
    cursor += END_DUR
    return sections, audio_tags, timeline, round(cursor, 2)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("story_json", type=Path)
    ap.add_argument("--out", type=Path, required=True, help="project dir to create")
    ap.add_argument("--no-audio", action="store_true",
                    help="skip TTS narration; pace scenes from text length")
    ap.add_argument("--force", action="store_true",
                    help="write into an existing project dir")
    ap.add_argument("--tts-base", default=TTS_DEFAULT)
    args = ap.parse_args()

    try:
        story = json.loads(args.story_json.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(f"story not found: {args.story_json}")
    except json.JSONDecodeError as e:
        fail(f"invalid JSON in {args.story_json}: {e}")

    title = str(story.get("title", "")).strip()
    if not title:
        fail("story needs a title")
    width = int(story.get("width", 1080))
    height = int(story.get("height", 1440))
    if width <= 0 or height <= 0:
        fail("width and height must be positive")
    composition = str(story.get("composition_id", "")).strip() or "mandarin-story"
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", composition):
        fail(f"composition_id must be lowercase ascii/dash: {composition}")
    bgm = str(story.get("bgm", "")).strip()
    bgm_volume = float(story.get("bgm_volume", 0.15))
    if not 0 < bgm_volume <= 1:
        fail("bgm_volume must be in (0, 1]")

    out = args.out.expanduser().resolve()
    if out.exists() and not args.force:
        fail(f"refusing to write into existing {out} — new dir per build, or --force")
    (out / "assets" / "audio").mkdir(parents=True, exist_ok=True)
    (out / "assets" / "vendor").mkdir(parents=True, exist_ok=True)

    gsap = SKILL_ROOT / "node_modules" / "gsap" / "dist" / "gsap.min.js"
    if not gsap.is_file():
        fail(f"gsap not found — run `npm install` in {SKILL_ROOT}")
    shutil.copy(gsap, out / "assets" / "vendor" / "gsap.min.js")

    bgm_data = None
    if bgm:
        bgm_src = Path(bgm).expanduser()
        if not bgm_src.is_file():
            fail(f"bgm file not found: {bgm_src} (use audio you have rights to)")
        shutil.copy(bgm_src, out / "assets" / "audio" / "bgm.mp3")
        bgm_data = {"volume": bgm_volume}

    sections, audio_tags, timeline, total = resolve_scenes(
        story, out, not args.no_audio, args.tts_base)
    if total > 90:
        warn(f"total duration {total:.0f}s — over ~90s is long for shorts platforms")

    if bgm_data:
        audio_tags.append(
            f'    <audio id="bgm" src="assets/audio/bgm.mp3" data-start="0" '
            f'data-duration="{total:g}" data-track-index="60" '
            f'data-volume="{bgm_volume:g}"></audio>')

    template = SKILL_ROOT / "assets" / "story_page.html"
    if not template.is_file():
        fail(f"template not found: {template}")
    data = {"compositionId": composition, "duration": total,
            "bgm": bgm_data, "scenes": timeline}
    page = (template.read_text(encoding="utf-8")
            .replace("{{TITLE}}", html.escape(title))
            .replace("{{COMPOSITION_ID}}", composition)
            .replace("{{WIDTH}}", str(width))
            .replace("{{HEIGHT}}", str(height))
            .replace("{{UNIT}}", f"{width / 1080:.4g}")
            .replace("{{DURATION}}", f"{total:g}")
            .replace("{{SCENES_HTML}}", "\n".join(sections))
            .replace("{{AUDIO_HTML}}", "\n".join(audio_tags))
            .replace("{{TIMELINE_DATA}}", json.dumps(data, ensure_ascii=False)))
    leftover = sorted(set(re.findall(r"\{\{[A-Z_]+\}\}", page)))
    if leftover:
        fail(f"unfilled placeholders: {', '.join(leftover)}")
    (out / "index.html").write_text(page, encoding="utf-8")
    (out / "build-manifest.json").write_text(
        json.dumps({"title": title, "total": total, "audio": not args.no_audio,
                    "scenes": timeline}, ensure_ascii=False, indent=1),
        encoding="utf-8")

    narration = f"{len(audio_tags) - (1 if bgm_data else 0)} narration clips" \
        if not args.no_audio else "no audio"
    print(f"OK: {out}/index.html ({len(timeline) - 2} sentences + title/end, "
          f"{total:g}s, {narration})")
    print("next (never overwrite an old render — bump the -v number):")
    print(f"  cd {SKILL_ROOT} && npx hyperframes check {out} --json")
    print(f"  cd {SKILL_ROOT} && npx hyperframes render {out} "
          f"--output {out}/renders/story-v1.mp4 --workers 1")


if __name__ == "__main__":
    main()
