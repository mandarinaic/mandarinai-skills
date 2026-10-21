#!/usr/bin/env python3
"""Build an offline MandarinAi video project from an editorial JSON brief."""

import argparse
import html
import json
import math
import re
import shutil
import subprocess
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from production_support import load_cast, resolve_speaker, timing_config, snap_end_frame, cue_times

ROOT = Path(__file__).resolve().parent.parent
FORMATS = {"portrait": (1080, 1920), "landscape": (1920, 1080), "square": (1080, 1080)}
LAYOUTS = {"hero", "lesson", "facts", "comparison", "screenshot", "cta"}
HANZI = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\U00020000-\U000323af]")


def fail(message):
    raise ValueError(message)


def string(value, label, maximum=2000, allow_empty=False):
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        fail(f"{label} must be a {'possibly empty ' if allow_empty else 'nonempty '}string")
    if len(value) > maximum:
        fail(f"{label} exceeds {maximum} characters; split the content into scenes")
    return value.strip()


def number(value, label, low=0, high=120, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        fail(f"{label} must be a finite number")
    if value < low or value > high or (positive and value <= 0):
        fail(f"{label} must be {'greater than' if positive else 'at least'} {low}, and at most {high}")
    return value


def integer(value, label, low, high):
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        fail(f"{label} must be an integer from {low} to {high}")
    return value


def load_json(path):
    with path.open(encoding="utf-8") as file:
        result = json.load(file)
    if not isinstance(result, dict):
        fail(f"{path}: expected a JSON object")
    return result


def local_file(value, base, label):
    raw = string(value, label)
    if urllib.parse.urlsplit(raw).scheme or raw.startswith("//"):
        fail(f"{label} must be a local file, not a URL")
    path = (base / raw).resolve()
    if not path.is_file():
        fail(f"{label} does not exist: {path}")
    return path


def audio_duration(path):
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type", "-of", "json", str(path)],
            check=True, capture_output=True, text=True,
        )
        probe = json.loads(result.stdout)
        duration = float(probe["format"]["duration"])
        if duration <= 0 or not math.isfinite(duration) or not any(s.get("codec_type") == "audio" for s in probe.get("streams", [])):
            fail(f"no measurable audio stream: {path}")
        return duration
    except FileNotFoundError:
        fail("ffprobe is required to measure audio; install ffmpeg first")
    except (subprocess.CalledProcessError, KeyError, json.JSONDecodeError):
        fail(f"ffprobe could not read audio: {path}")


def ruby_text(text, pinyin):
    if pinyin is None:
        return html.escape(text)
    if isinstance(pinyin, str):
        syllables = pinyin.split()
    elif isinstance(pinyin, list) and all(isinstance(s, str) and s.strip() and not re.search(r"\s", s) for s in pinyin):
        syllables = pinyin
    else:
        fail("pinyin must be space-separated syllables or a list, with one syllable per Hanzi")
    syllables = [unicodedata.normalize("NFC", s.strip().lower()) for s in syllables]
    if not all(re.fullmatch(r"[a-züāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜńňǹḿê]{1,12}", s) for s in syllables):
        fail("pinyin syllables must use Latin letters with optional tone marks; tone numbers, punctuation, and nonletter tokens are rejected")
    if len(syllables) != len(HANZI.findall(text)):
        fail(f"pinyin has {len(syllables)} syllables but text has {len(HANZI.findall(text))} Hanzi; supply one per Hanzi, excluding punctuation")
    iterator = iter(syllables)
    return "".join(f"<ruby>{html.escape(c)}<rt>{html.escape(next(iterator))}</rt></ruby>" if HANZI.fullmatch(c) else html.escape(c) for c in text)


def srt_time(seconds):
    ms = max(0, round(seconds * 1000))
    hours, ms = divmod(ms, 3600000)
    minutes, ms = divmod(ms, 60000)
    seconds, ms = divmod(ms, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{ms:03}"


def fetch_tts(text, voice, url, path):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in {"https", "http"} or not parsed.netloc:
        fail("--tts-url must be an HTTP(S) endpoint")
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    query = [(k, v) for k, v in query if k not in {"text", "voice"}]
    request_url = urllib.parse.urlunsplit(parsed._replace(query=urllib.parse.urlencode(query + [("text", text), ("voice", voice)])))
    try:
        request = urllib.request.Request(request_url, headers={"Accept": "audio/mpeg, audio/*", "User-Agent": "MandarinAi-Video/1.0"})
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read(20 * 1024 * 1024 + 1)
        if not data or len(data) > 20 * 1024 * 1024:
            fail("TTS response is empty or exceeds 20 MiB")
        path.write_bytes(data)
    except (urllib.error.URLError, TimeoutError) as error:
        fail(f"TTS request failed (no silent fallback): {error}")


def speaker_name(profile):
    return " ".join(value for value in (profile["name"], profile.get("hanzi", "")) if value)


def safe_json(value):
    return (json.dumps(value, ensure_ascii=False, allow_nan=False)
            .replace("<", "\\u003c").replace("&", "\\u0026")
            .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


def build(args):
    brief_path = Path(args.brief).resolve()
    brief = load_json(brief_path)
    base = brief_path.parent
    out = Path(args.out).resolve()
    if out.exists():
        fail(f"output directory already exists: {out}; choose a new directory")
    source = load_json(local_file(args.source, Path.cwd(), "--source") if args.source
                       else local_file(brief.get("source"), base, "source"))
    if source.get("kind") not in {"word", "grammar", "university", "article"}:
        fail("source.kind must be word, grammar, university, or article")
    if not isinstance(source.get("id"), (str, int)) or isinstance(source.get("id"), bool) or not str(source["id"]).strip():
        fail("source.id must be a nonempty string or integer")
    for key in ("title", "url", "language"):
        string(source.get(key), f"source.{key}")
    if not isinstance(source.get("content"), dict):
        fail("source.content must be an object")
    source_url = urllib.parse.urlsplit(source["url"])
    if source_url.scheme not in {"http", "https"} or not source_url.netloc:
        fail("source.url must be a complete HTTP(S) URL")
    mode = brief.get("mode")
    if mode not in {"promo", "tutorial"}:
        fail("mode must be promo or tutorial")
    format_name = brief.get("format", "portrait")
    if format_name not in FORMATS:
        fail("format must be portrait, landscape, or square")
    width, height = FORMATS[format_name]
    if ("width" in brief) != ("height" in brief):
        fail("width and height must be supplied together")
    if "width" in brief:
        width = integer(brief["width"], "width", 2, 7680)
        height = integer(brief["height"], "height", 2, 7680)
        if width % 2 or height % 2:
            fail("width and height must be even")
    fps = integer(brief.get("fps", 30), "fps", 1, 60)
    style = brief.get("style", "clean")
    if style not in {"clean", "editorial", "ink"}:
        fail("style must be clean, editorial, or ink")
    title = string(brief.get("title", source["title"]), "title", 180)
    inputs = brief.get("scenes")
    if not isinstance(inputs, list) or not 1 <= len(inputs) <= 24:
        fail("scenes must contain 1 to 24 scene objects")
    timing = timing_config(brief.get("timing"))
    named = any(isinstance(s, dict) and (s.get("speaker") is not None or "lines" in s) for s in inputs)
    cast = load_cast(brief.get("cast", {} if named else None), ROOT / "assets")

    # Validate all local inputs before creating files or requesting narration.
    prepared = []
    for i, scene in enumerate(inputs, 1):
        if not isinstance(scene, dict) or scene.get("layout") not in LAYOUTS:
            fail(f"scene {i}: invalid layout")
        data = dict(scene)
        data["heading"] = string(scene.get("heading"), f"scene {i} heading", 120)
        for key in ("text", "translation", "label", "caption", "narration"):
            data[key] = string(scene.get(key, ""), f"scene {i} {key}", 1000, allow_empty=True)
        data["text_html"] = ruby_text(data["text"], scene.get("pinyin"))
        profile = resolve_speaker(cast, scene.get("speaker"))
        data["profile"] = profile
        show = scene.get("show_presenter", True)
        if not isinstance(show, bool):
            fail(f"scene {i}: show_presenter must be true or false")
        data["show_presenter"] = show
        data["hold"] = number(scene.get("hold", 1), f"scene {i} hold", high=30)
        beats = scene.get("beats")
        if beats is not None and timing is None:
            fail(f"scene {i}: beats requires timing.bpm")
        beat_duration = number(beats, f"scene {i} beats", high=1024, positive=True) * timing["seconds_per_beat"] if beats is not None else 0
        data["duration"] = max(number(scene.get("duration", beat_duration or 4), f"scene {i} duration", positive=True), beat_duration)
        if scene.get("snap") is not None and scene["snap"] not in {"none", "beat", "bar"}:
            fail(f"scene {i}: snap must be none, beat, or bar")
        cue_times(scene.get("cues", []), 120, fps, timing)
        bullets = scene.get("bullets", [])
        if not isinstance(bullets, list) or len(bullets) > 6:
            fail(f"scene {i}: bullets must be a list of at most 6 strings")
        data["bullets"] = [string(b, f"scene {i} bullet", 180) for b in bullets]
        data["image_path"] = local_file(scene["image"], base, f"scene {i} image") if scene.get("image") else None
        if data["image_path"] and data["image_path"].suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            fail(f"scene {i}: image must be a local PNG, JPEG, or WebP raster")
        if scene["layout"] == "screenshot" and not data["image_path"]:
            fail(f"scene {i}: screenshot layout requires a local image")
        has_lines = "lines" in scene
        if has_lines:
            lines = scene["lines"]
            if not isinstance(lines, list) or not 1 <= len(lines) <= 4:
                fail(f"scene {i}: lines must contain 1 to 4 dialogue utterances")
            if data["narration"] or scene.get("audio"):
                fail(f"scene {i}: use lines or narration/audio, not both")
        else:
            lines = [{"speaker": scene.get("speaker"), "text": data["narration"],
                      "audio": scene.get("audio"), "caption": data["caption"]}]
        speech = []
        for j, line in enumerate(lines, 1):
            if not isinstance(line, dict):
                fail(f"scene {i} line {j}: expected an object")
            if has_lines and not line.get("speaker"):
                fail(f"scene {i} line {j}: a named speaker is required")
            person = resolve_speaker(cast, line.get("speaker")) if has_lines else profile
            text = string(line.get("text", ""), f"scene {i} line {j} text", 1000, allow_empty=not has_lines)
            if len(text.encode("utf-16-le")) // 2 > 200:
                fail(f"scene {i} line {j}: narration exceeds Swan's 200 UTF-16 character limit")
            path = local_file(line["audio"], base, f"scene {i} line {j} audio") if line.get("audio") else None
            measured = audio_duration(path) if path else 0
            if text and not path and not args.tts and not args.silent:
                fail(f"scene {i}: narration needs local audio or --tts; use --silent only for an explicitly silent draft")
            gap = number(line.get("pause_after", .35 if j < len(lines) else 0),
                         f"scene {i} line {j} pause_after", high=30)
            translation = string(line.get("translation", ""), f"scene {i} line {j} translation", 800, allow_empty=True)
            caption = string(line.get("caption", ""), f"scene {i} line {j} caption", 1000, allow_empty=True) or text
            speech.append({"profile": person, "text": text, "text_html": ruby_text(text, line.get("pinyin")) if has_lines else "",
                           "pinyin": line.get("pinyin"), "translation": translation, "caption": caption,
                           "audio_path": path, "measured": measured, "pause_after": gap})
        data["speech"] = speech
        data["has_lines"] = has_lines
        data["named_tracks"] = has_lines or profile is not None
        if has_lines:
            data["narration"] = "\n".join(line["text"] for line in speech)
        prepared.append(data)
    bgm_path = local_file(brief["bgm"], base, "bgm") if brief.get("bgm") else None
    bgm_seconds = audio_duration(bgm_path) if bgm_path else 0
    bgm_volume = number(brief.get("bgm_volume", .12), "bgm_volume", high=1)
    bgm_duck = brief.get("bgm_duck", True)
    if not isinstance(bgm_duck, bool):
        fail("bgm_duck must be true or false")
    template = (ROOT / "assets/project-scene.html").read_text(encoding="utf-8")
    out.mkdir(parents=True, exist_ok=False)
    try:
        (out / "assets").mkdir()
        (out / "scenes").mkdir()
        for name in ("mandarinai-logo.png", "mandarinai-icon.png"):
            shutil.copyfile(ROOT / "assets/brand" / name, out / "assets" / name)
        if cast["characters"]:
            (out / "assets/cast").mkdir()
            for person in cast["characters"].values():
                filename = person["portrait"]
                shutil.copyfile(ROOT / "assets/cast" / filename, out / "assets/cast" / filename)
                person["portrait"] = f"assets/cast/{filename}"
        (out / "source.json").write_text(json.dumps(source, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        scenes, subtitles = [], []
        total_frames = 0
        script = [f"# {title}", "", f"Source: {source['url']}",
                  f"Mode: {mode} · Style: {style} · {width}×{height} · {fps} fps",
                  "Phrase-level captions; measured speech timing, without character alignment.", ""]
        if timing:
            script.extend([f"Tempo: {timing['bpm']} BPM · {timing['beats_per_bar']} beats/bar · snap {timing['snap']}", ""])
        for i, data in enumerate(prepared, 1):
            image_path = None
            if data["image_path"]:
                image_path = f"assets/scene-{i:02}-image{data['image_path'].suffix.lower()}"
                shutil.copyfile(data["image_path"], out / image_path)
            tracks, dialogue = [], []
            cursor, speech_end = .5, 0
            single_audio, single_seconds = None, 0
            for j, line in enumerate(data["speech"], 1):
                person = line["profile"]
                voice = person["voice"] if person else (getattr(args, "voice", None) or "zh-CN-XiaoxiaoNeural")
                prefix = f"scene-{i:02}-line-{j:02}" if data["has_lines"] else f"scene-{i:02}"
                path, seconds, provenance = None, 0, None
                if not args.silent and line["audio_path"]:
                    path = f"assets/{prefix}-audio{line['audio_path'].suffix.lower()}"
                    shutil.copyfile(line["audio_path"], out / path)
                    seconds, provenance = line["measured"], "local"
                elif not args.silent and line["text"] and args.tts:
                    path = f"assets/{prefix}-voice.mp3"
                    fetch_tts(line["text"], voice, args.tts_url, out / path)
                    seconds, provenance = audio_duration(out / path), "tts"
                if args.silent and data["named_tracks"] and (line["text"] or line["audio_path"]):
                    seconds = line["measured"] or max(.8, len(HANZI.findall(line["text"])) * .26)
                if path:
                    tracks.append({"file": path, "speaker": person["id"] if person else None,
                                   "voice": voice if provenance == "tts" else None, "source": provenance,
                                   "start": cursor, "duration": seconds, "caption": line["caption"]})
                if data["has_lines"]:
                    dialogue.append({"speaker": person["id"], "text": line["text"], "pinyin": line["pinyin"],
                                     "translation": line["translation"], "caption": line["caption"],
                                     "start": cursor, "duration": seconds, "audio": path,
                                     "timing_method": "estimated" if args.silent else "measured"})
                if path or (args.silent and data["named_tracks"] and seconds):
                    speech_end = cursor + seconds
                    cursor = speech_end + line["pause_after"]
                if not data["has_lines"]:
                    single_audio, single_seconds = path, seconds if path else 0
            minimum = max(data["duration"], cursor + data["hold"] if speech_end else 0)
            end_frame = max(total_frames + 1, snap_end_frame(total_frames, minimum, fps, timing, data.get("snap")))
            frames = end_frame - total_frames
            duration, start = frames / fps, total_frames / fps
            if duration > 120:
                fail(f"scene {i}: audio/hold/grid require {duration:.3f}s; split the scene")
            cues = cue_times(data.get("cues", []), duration, fps, timing)
            person = data["profile"] or (data["speech"][0]["profile"] if data["has_lines"] else None)
            caption = data["caption"] or data["narration"]
            item = {"file": f"scenes/scene-{i:02}.html", "layout": data["layout"], "heading": data["heading"],
                    "start": start, "duration": duration, "frames": frames, "narration": data["narration"],
                    "audio": single_audio, "audio_duration": single_seconds,
                    "audio_offset": .5 if single_audio else 0, "caption": caption,
                    "speaker": person["id"] if person else None, "lines": dialogue, "cues": cues,
                    "minimum_duration": minimum, "hold": data["hold"],
                    "pending_narration": bool(args.silent and any(l["text"] or l["audio_path"] for l in data["speech"]))}
            if data["named_tracks"]:
                item["voice_tracks"] = tracks
            scenes.append(item)
            total_frames = end_frame
            presenter_html = ""
            if person and data["show_presenter"]:
                presenter_html = (f'<aside class="presenter-strip"><img class="presenter-portrait" '
                                  f'src="../{person["portrait"]}" alt="{html.escape(person["name"], quote=True)}">'
                                  f'<div><strong class="presenter-name">{html.escape(speaker_name(person))}</strong>'
                                  f'<span class="presenter-role">{html.escape(person["role"])}</span></div></aside>')
            dialogue_html = ""
            if dialogue:
                articles = []
                for line, prepared_line in zip(dialogue, data["speech"]):
                    profile = cast["characters"][line["speaker"]]
                    articles.append(
                        f'<article class="dialogue-line" data-speaker="{profile["id"]}" '
                        f'data-line-start="{line["start"]}" data-line-end="{line["start"] + line["duration"]}">'
                        f'<img class="dialogue-portrait" src="../{profile["portrait"]}" alt="{profile["name"]}">'
                        f'<div><div class="speaker-name">{html.escape(speaker_name(profile))}</div>'
                        f'<p class="line-chinese">{prepared_line["text_html"]}</p>'
                        f'<p class="line-translation">{html.escape(line["translation"])}</p></div></article>')
                dialogue_html = '<div class="dialogue-lines">' + "".join(articles) + '</div>'
            payload = {"duration": duration, "speaker": item["speaker"], "presenter": person,
                       "cast": cast["characters"], "lines": dialogue,
                       "voice_tracks": tracks, "timing": timing, "cues": cues}
            replacements = {
                "TITLE": html.escape(title), "STYLE": style, "LAYOUT": data["layout"], "MODE": mode,
                "DURATION": str(duration), "WIDTH": str(width), "HEIGHT": str(height),
                "LABEL": html.escape(data["label"] or f"{source['kind']} · {mode}"),
                "HEADING": html.escape(data["heading"]), "TEXT": data["text_html"],
                "TRANSLATION": html.escape(data["translation"]),
                "FOOTER": html.escape(source["url"] if data["layout"] == "cta" else (data["label"] or source_url.netloc)),
                "BULLETS": "".join(f'<li data-enter="{.45 + n * .12:.2f}"><span>{n+1:02}</span><div>{html.escape(b)}</div></li>' for n,b in enumerate(data["bullets"])),
                "IMAGE": f'<figure data-enter=".30"><img src="../{image_path}" alt="{html.escape(data["heading"], quote=True)}"></figure>' if image_path else "",
                "INDEX": f"{i:02}", "COUNT": f"{len(prepared):02}",
                "SCENE_DATA": safe_json(payload), "PRESENTER_HTML": presenter_html, "DIALOGUE_HTML": dialogue_html,
            }
            scene_html = re.sub(r"@@([A-Z_]+)@@", lambda match: replacements[match[1]], template)
            (out / item["file"]).write_text(scene_html, encoding="utf-8")
            # One subtitle per measured utterance; silent drafts use estimated line timing.
            entries = dialogue if dialogue else [{"start": .5 if single_audio else .35,
                       "duration": single_seconds if single_audio else max(0, duration - .5), "caption": caption}]
            for entry in entries:
                text = entry["caption"]
                cue_start = start + entry["start"]
                cue_end = min(start + duration - .05, cue_start + entry["duration"])
                if text and cue_end > cue_start:
                    subtitles.append(f"{len(subtitles)+1}\n{srt_time(cue_start)} --> {srt_time(cue_end)}\n{text}\n")
            script.extend([f"## {i:02} · {data['heading']}", f"{start:.3f}s–{start+duration:.3f}s · {data['layout']}",
                           "", data["text"], data["translation"], ""])
            for line in data["speech"]:
                label = speaker_name(line["profile"]) if line["profile"] else "Narrator"
                script.extend([f"{label}: {line['text'] or '(recording without script)'}"])
            script.extend([f"Audio: {'PENDING — explicitly silent draft' if item['pending_narration'] else ', '.join(t['file'] for t in tracks) or 'none'}", ""])
        bgm = None
        if bgm_path and not args.silent:
            bgm = {"file": f"assets/bgm{bgm_path.suffix.lower()}", "duration": bgm_seconds,
                   "volume": bgm_volume, "duck": bgm_duck}
            shutil.copyfile(bgm_path, out / bgm["file"])
        has_voice = any(s.get("voice_tracks") or s["audio"] for s in scenes)
        manifest = {"schema_version": 1, "title": title, "mode": mode, "style": style, "format": format_name,
                    "dimensions": {"width": width, "height": height}, "fps": fps,
                    "duration": total_frames / fps, "frames": total_frames, "source": source,
                    "source_snapshot": "source.json", "cast": cast, "timing": timing,
                    "audio_mode": "narrated" if has_voice else "music" if bgm else "silent",
                    "pending_narration": any(s["pending_narration"] for s in scenes), "bgm": bgm,
                    "caption_timing": "Phrase-level per utterance; measured where audio exists, estimated in silent drafts. No forced character alignment.",
                    "scenes": scenes}
        (out / "project.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        (out / "captions.srt").write_text("\n".join(subtitles), encoding="utf-8")
        (out / "script.md").write_text("\n".join(script), encoding="utf-8")
        (out / "preview.html").write_text(preview_html(manifest), encoding="utf-8")
    except Exception:
        shutil.rmtree(out)
        raise
    print(f"Project: {out}\n{len(scenes)} scenes · {manifest['duration']:.3f}s · {width}×{height} · {fps} fps · audio: {manifest['audio_mode']}")
    if manifest["pending_narration"]:
        print("Narration is PENDING: --silent intentionally omitted the voice tracks. See script.md.")



def preview_html(manifest):
    payload = json.dumps({"scenes": manifest["scenes"], "dimensions": manifest["dimensions"]}, ensure_ascii=False).replace("<", "\\u003c").replace("&", "\\u0026")
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(manifest['title'])} — preview</title>
<style>body{{margin:0;background:#e7ebe9;color:#16382b;font:16px system-ui}}header{{display:flex;gap:14px;align-items:center;flex-wrap:wrap;padding:14px 20px}}select,input,button{{font:inherit}}input{{flex:1;min-width:130px}}iframe{{display:block;border:0;transform-origin:top left;background:white}}#stage{{margin:auto;overflow:hidden}}small{{display:block;padding:0 20px 14px}}#time{{font-variant-numeric:tabular-nums}}</style>
<header><strong>Scene preview</strong><select id="scene"></select><input id="seek" type="range" min="0" value="1" step="0.01"><output id="time"></output></header><small>Drag to inspect deterministic scene time. This preview is silent; project rendering mixes measured audio. Captions: phrase-level, one cue per spoken utterance.</small><div id="stage"><iframe title="Video scene" id="frame"></iframe></div>
<script>const project={payload};const picker=document.querySelector('#scene'),slider=document.querySelector('#seek'),frame=document.querySelector('#frame'),stage=document.querySelector('#stage');project.scenes.forEach((s,i)=>{{const o=document.createElement('option');o.value=i;o.textContent=`${{i+1}} · ${{s.heading}}`;picker.append(o)}});function resize(){{const d=project.dimensions,w=Math.min(innerWidth-32,(innerHeight-130)*d.width/d.height),scale=w/d.width;stage.style.width=w+'px';stage.style.height=d.height*scale+'px';frame.style.width=d.width+'px';frame.style.height=d.height+'px';frame.style.transform=`scale(${{scale}})`}}function seek(){{const t=Number(slider.value);document.querySelector('#time').textContent=t.toFixed(2)+' s';frame.contentWindow.postMessage({{type:'mandarinai:seek',seconds:t}},'*')}}function choose(){{const s=project.scenes[Number(picker.value)];slider.max=s.duration;slider.value=Math.min(1,s.duration);frame.src=s.file}}frame.onload=seek;picker.onchange=choose;slider.oninput=seek;window.onresize=resize;resize();choose();</script></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__, epilog="All inputs are local except explicitly requested --tts calls. No production API writes. Existing output directories are refused.")
    parser.add_argument("brief", help="JSON brief; source, image, audio, and bgm paths are relative to this file")
    parser.add_argument("--out", required=True, help="new project directory")
    parser.add_argument("--source", help="override source JSON path (relative to the current directory, not the brief)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--tts", action="store_true", help="request voice audio for narration via Swan-compatible GET /tts")
    group.add_argument("--silent", action="store_true", help="explicitly omit all voice/music audio and mark narration pending")
    parser.add_argument("--tts-url", default="https://www.mandarinai.com/tts", help="TTS GET endpoint (only used with --tts)")
    parser.add_argument("--voice", help="unnamed narrator voice; named cast uses registry/overrides")
    args = parser.parse_args()
    try:
        build(args)
    except (ValueError, OSError, json.JSONDecodeError) as error:
        parser.exit(1, f"error: {error}\n")


if __name__ == "__main__":
    main()
