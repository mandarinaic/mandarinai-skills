#!/usr/bin/env python3
"""Render a built MandarinAi project, mix measured audio, and verify the MP4."""

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def fail(message):
    raise ValueError(message)


def finite(value, label, low=0, high=100000, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high or (positive and value <= 0):
        fail(f"{label} is invalid")
    return value


def integer(value, label, low, high):
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        fail(f"{label} must be an integer from {low} to {high}")
    return value


def local(project, relative, label):
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        fail(f"{label} must be a project-relative path")
    path = (project / relative).resolve()
    if not path.is_relative_to(project) or not path.is_file():
        fail(f"{label} is missing or outside the project: {relative}")
    return path


def run(command):
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        fail(f"{Path(command[0]).name} failed ({result.returncode}):\n{result.stderr[-4000:]}")
    return result.stdout


def probe(path):
    return json.loads(run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)]))


def measured_audio(path):
    data = probe(path)
    if not any(s.get("codec_type") == "audio" for s in data.get("streams", [])):
        fail(f"no audio stream in {path}")
    value = float(data["format"]["duration"])
    if not math.isfinite(value) or value <= 0:
        fail(f"unmeasurable audio: {path}")
    return value


def validate(project, manifest):
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        fail("project.json must use schema_version 1")
    dimensions = manifest.get("dimensions", {})
    width = integer(dimensions.get("width"), "width", 2, 7680)
    height = integer(dimensions.get("height"), "height", 2, 7680)
    if width % 2 or height % 2:
        fail("dimensions must be even")
    fps = integer(manifest.get("fps"), "fps", 1, 60)
    if manifest.get("audio_mode") not in {"narrated", "music", "silent"}:
        fail("audio_mode must be narrated, music, or silent")
    scenes = manifest.get("scenes")
    if not isinstance(scenes, list) or not 1 <= len(scenes) <= 24:
        fail("project must contain 1 to 24 scenes")
    total_frames = 0
    for i, scene in enumerate(scenes, 1):
        if not isinstance(scene, dict):
            fail(f"scene {i} must be an object")
        scene["html_path"] = local(project, scene.get("file"), f"scene {i} file")
        if scene["html_path"].suffix.lower() != ".html":
            fail(f"scene {i} file must be HTML")
        frames = integer(scene.get("frames"), f"scene {i} frames", 1, fps * 120)
        duration = finite(scene.get("duration"), f"scene {i} duration", high=120, positive=True)
        start = finite(scene.get("start"), f"scene {i} start")
        if abs(duration - frames / fps) > 1e-7 or abs(start - total_frames / fps) > 1e-7:
            fail(f"scene {i}: frame count, duration, and contiguous start do not agree")
        total_frames += frames
        scene["audio_path"] = local(project, scene["audio"], f"scene {i} audio") if scene.get("audio") else None
        if scene["audio_path"]:
            if manifest["audio_mode"] == "silent":
                fail("a silent manifest cannot contain narration audio")
            offset = finite(scene.get("audio_offset"), f"scene {i} audio_offset", high=120)
            actual = measured_audio(scene["audio_path"])
            recorded = finite(scene.get("audio_duration"), f"scene {i} audio_duration", positive=True)
            if abs(actual - recorded) > 0.15:
                fail(f"scene {i} audio duration changed; rebuild the project")
            if offset + actual > duration + 1 / fps:
                fail(f"scene {i} narration extends past its scene; rebuild with a longer duration")
    if manifest.get("frames") != total_frames or abs(finite(manifest.get("duration"), "duration", positive=True) - total_frames / fps) > 1e-7:
        fail("project frame count and duration do not match its scenes")
    if manifest.get("bgm"):
        bgm = manifest["bgm"]
        if not isinstance(bgm, dict) or manifest["audio_mode"] == "silent":
            fail("bgm is invalid for this audio_mode")
        bgm["path"] = local(project, bgm.get("file"), "bgm file")
        bgm["volume"] = finite(bgm.get("volume"), "bgm volume", high=1)
        measured_audio(bgm["path"])
    expected_audio = any(s["audio_path"] for s in scenes) or bool(manifest.get("bgm"))
    if (manifest["audio_mode"] != "silent") != expected_audio:
        fail("audio_mode disagrees with the available audio tracks")
    return width, height, fps, total_frames, expected_audio


def concat_line(path):
    # ffmpeg concat demuxer quoting, not shell quoting; even a temp root may contain an apostrophe.
    return "file '" + str(path).replace("'", "'\\''") + "'\n"


def render(args):
    project = Path(args.project).resolve()
    manifest_path = project / "project.json"
    with manifest_path.open(encoding="utf-8") as file:
        manifest = json.load(file)
    width, height, fps, total_frames, expected_audio = validate(project, manifest)
    output = Path(args.output).resolve()
    if output.suffix.lower() != ".mp4":
        fail("--output must end in .mp4")
    report_path = output.with_suffix(".verification.json")
    qa_dir = output.parent / f"{output.stem}-qa"
    for destination in (output, report_path, qa_dir):
        if destination.exists():
            fail(f"output already exists: {destination}; choose a new output name")
    if output.is_relative_to(project):
        fail("render output must be outside the project directory to preserve the build")
    browser = Path(args.browser).resolve() if args.browser else None
    if browser and not browser.is_file():
        fail(f"browser does not exist: {browser}")
    for tool in ("node", "ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            fail(f"{tool} is required and was not found on PATH")
    output.parent.mkdir(parents=True, exist_ok=True)
    duration = total_frames / fps
    with tempfile.TemporaryDirectory(prefix="mandarinai-render-") as temporary:
        work = Path(temporary)
        parts = []
        for i, scene in enumerate(manifest["scenes"], 1):
            part = work / f"part-{i:02}.mp4"
            print(f"Rendering scene {i}/{len(manifest['scenes'])}: {scene.get('heading', scene['file'])}", flush=True)
            command = ["node", str(ROOT / "scripts" / "render.mjs"), "-o", str(part), "-d", str(scene["duration"]), "-s", f"{width}x{height}", "-f", str(fps)]
            if browser:
                command.extend(["--browser", str(browser)])
            command.extend(["--", str(scene["html_path"])])
            run(command)
            parts.append(part)
        concat_path = work / "parts.txt"
        concat_path.write_text("".join(concat_line(path) for path in parts), encoding="utf-8")
        joined = work / "joined.mp4"
        run(["ffmpeg", "-n", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(concat_path), "-map", "0:v:0", "-c:v", "copy", str(joined)])
        completed = work / "completed.mp4"
        if expected_audio:
            command = ["ffmpeg", "-n", "-v", "error", "-i", str(joined)]
            filters, tracks = [], []
            input_index = 1
            for scene in manifest["scenes"]:
                if not scene["audio_path"]:
                    continue
                command.extend(["-i", str(scene["audio_path"])])
                offset_ms = round((scene["start"] + scene["audio_offset"]) * 1000)
                label = f"voice{input_index}"
                filters.append(f"[{input_index}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,loudnorm=I=-16:TP=-1.5:LRA=11,adelay={offset_ms}:all=1[{label}]")
                tracks.append(f"[{label}]")
                input_index += 1
            if manifest.get("bgm"):
                bgm = manifest["bgm"]
                command.extend(["-stream_loop", "-1", "-i", str(bgm["path"])])
                fade = min(1.5, duration / 4)
                filters.append(f"[{input_index}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,volume={bgm['volume']},atrim=duration={duration},afade=t=in:st=0:d={fade},afade=t=out:st={duration - fade}:d={fade}[music]")
                tracks.append("[music]")
            filters.append("".join(tracks) + f"amix=inputs={len(tracks)}:duration=longest:normalize=0,alimiter=limit=0.95:level=0,apad,atrim=duration={duration},asetpts=N/SR/TB[audio]")
            command.extend(["-filter_complex", ";".join(filters), "-map", "0:v:0", "-map", "[audio]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", str(duration), "-movflags", "+faststart", str(completed)])
            run(command)
        else:
            run(["ffmpeg", "-n", "-v", "error", "-i", str(joined), "-map", "0:v:0", "-c:v", "copy", "-an", "-t", str(duration), "-movflags", "+faststart", str(completed)])
        evidence = probe(completed)
        video = next((s for s in evidence.get("streams", []) if s.get("codec_type") == "video"), None)
        audio = next((s for s in evidence.get("streams", []) if s.get("codec_type") == "audio"), None)
        actual_duration = float(evidence["format"]["duration"])
        actual_fps = float(Fraction(video["avg_frame_rate"])) if video else 0
        if not video or video.get("codec_name") != "h264" or video.get("pix_fmt") != "yuv420p":
            fail("render did not produce H.264 yuv420p video")
        if video.get("width") != width or video.get("height") != height or abs(actual_fps - fps) > 0.001:
            fail("render dimensions or frame rate do not match the project")
        if abs(actual_duration - duration) > 2 / fps + 0.001:
            fail(f"render duration {actual_duration:.6f}s differs from expected {duration:.6f}s by more than 2 frames")
        if bool(audio) != expected_audio or (audio and audio.get("codec_name") != "aac"):
            fail("render audio does not match the project")
        audio_seconds = float(audio.get("duration", 0)) if audio else 0
        if audio and abs(audio_seconds - duration) > 2 / fps + 0.001:
            fail(f"audio lasts {audio_seconds:.6f}s instead of the full {duration:.6f}s video; closing CTA coverage failed")
        if video.get("nb_frames") and int(video["nb_frames"]) != total_frames:
            fail("render frame count does not match the project")
        qa_temp = work / "qa"
        qa_temp.mkdir()
        first = min(manifest["scenes"][0]["duration"] - 1 / fps, 1.0)
        times = [("first-content", first), ("midpoint", duration / 2), ("ending", max(0, duration - max(0.5, 1 / fps)))]
        frames = []
        for name, time in times:
            filename = f"{name}.png"
            run(["ffmpeg", "-n", "-v", "error", "-ss", str(max(0, time)), "-i", str(completed), "-frames:v", "1", "-update", "1", str(qa_temp / filename)])
            frames.append({"file": str(qa_dir / filename), "time": time})
        report = {"schema_version": 1, "output": str(output), "project": str(project), "expected_duration": duration, "duration": actual_duration, "width": video["width"], "height": video["height"], "fps": actual_fps, "frames": int(video.get("nb_frames", total_frames)), "video_codec": video["codec_name"], "pixel_format": video["pix_fmt"], "audio_expected": expected_audio, "audio_codec": audio["codec_name"] if audio else None, "audio_duration": audio_seconds if audio else None, "audio_mode": manifest["audio_mode"], "pending_narration": manifest.get("pending_narration", False), "caption_file": str(project / "captions.srt"), "caption_note": "Sidecar phrase-level captions; not burned in or character-aligned.", "checks": {"duration_within_two_frames": True, "dimensions_and_fps": True, "audio_expected": True, "audio_covers_full_video": bool(audio) if expected_audio else None, "h264_yuv420p": True}, "visual_qa": {"status": "pending human/agent inspection", "frames": frames}, "ffprobe": evidence}
        # Link creation is atomic and refuses replacement, including a racing output creation.
        staged = output.parent / f".{output.name}.{os.getpid()}.partial"
        try:
            with staged.open("xb") as file, completed.open("rb") as src:
                shutil.copyfileobj(src, file)
            os.link(staged, output)
        finally:
            staged.unlink(missing_ok=True)
        shutil.copytree(qa_temp, qa_dir)
        with report_path.open("x", encoding="utf-8") as file:
            json.dump(report, file, ensure_ascii=False, indent=2)
            file.write("\n")
    print(f"MP4: {output}\nVerified: {width}×{height} · {actual_fps:g} fps · {actual_duration:.3f}s · H.264 yuv420p · {'AAC audio' if audio else 'silent'}\nReport: {report_path}\nInspect QA frames: {qa_dir}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, epilog="Requires Node + this skill's Playwright dependency + Chromium, ffmpeg, and ffprobe. Existing outputs are never replaced. Voice/music are padded to the whole video, preserving the closing CTA.")
    parser.add_argument("project", help="built project directory containing project.json")
    parser.add_argument("--output", required=True, help="new .mp4 path outside the project directory")
    parser.add_argument("--browser", help="local Chromium/Chrome executable; otherwise Playwright Chromium")
    args = parser.parse_args()
    try:
        render(args)
    except (ValueError, OSError, KeyError, json.JSONDecodeError) as error:
        parser.exit(1, f"error: {error}\n")


if __name__ == "__main__":
    main()
