"""Review evidence for a rendered MP4: scan, cue, and phone-width sheets plus a motion advisory.

Adapted from dashi-animationstyle (MIT, https://github.com/chuspeeism/dashi-animationstyle):
its ``render.mjs --scan / --check-marks`` sheets and ``丰富度检查.mjs`` change metric.
The motion numbers here are advisory only. Teaching videos hold still on purpose for
reading and retrieval, so declared hold windows are exempt and nothing fails a render.
"""

import math
import subprocess
from pathlib import Path

SCAN_PER_SECOND = 3
SCAN_CELLS = 32
CUE_BEFORE = 0.1
CUE_AFTER = 0.35
CUES_PER_SHEET = 8
SHEET_PADDING = 6
SHEET_MARGIN = 6
PHONE_WIDTH = 480
MOTION_WIDTH = 160
MOTION_PER_SECOND = 10
CELL_SECONDS = 2.5
# Thresholds calibrated upstream on 1920x1080 explainer animations (one viewer, 3 pairs):
# mean absolute gray difference, 0-255. They are guidance for teaching video, not gates.
MOVING = 0.3
FLAT = 4
RICH = 10
STATIC_SECONDS = 2.0


def even(value):
    return max(2, int(round(value / 2)) * 2)


def cell_size(width, height):
    """Cells keep a 480-pixel long side, matching dashi's 480x270 landscape cells."""
    if width >= height:
        return 480, even(480 * height / width)
    return even(480 * width / height), 480


def scan_columns(width, height):
    return 4 if width >= height else 8


def sheet_size(columns, rows, cell_width, cell_height):
    return (columns * cell_width + (columns - 1) * SHEET_PADDING + 2 * SHEET_MARGIN,
            rows * cell_height + (rows - 1) * SHEET_PADDING + 2 * SHEET_MARGIN)


def frames_after(seconds, fps):
    # Subtract a hair so 0.1 * 30 (3.0000000000000004) stays three frames.
    return max(1, math.ceil(seconds * fps - 1e-9))


def scan_frames(total_frames, fps):
    step = max(1, round(fps / SCAN_PER_SECOND))
    return list(range(0, total_frames, step))


def cue_frames(manifest, fps, total_frames):
    """Each cue, as absolute frames 0.1 s before and 0.35 s after its reveal."""
    planned = []
    for index, scene in enumerate(manifest["scenes"], 1):
        first = round(scene["start"] * fps)
        for cue_id, cue in (scene.get("cues") or {}).items():
            local = cue.get("frame") if isinstance(cue, dict) else None
            if not isinstance(local, int):
                seconds = cue["seconds"] if isinstance(cue, dict) else cue
                local = math.ceil(seconds * fps - 1e-9)
            frame = min(total_frames - 1, first + local)
            planned.append({"scene": index, "heading": scene.get("heading"), "cue": cue_id,
                            "seconds": round(frame / fps, 6),
                            "before_frame": max(0, frame - frames_after(CUE_BEFORE, fps)),
                            "after_frame": min(total_frames - 1, frame + frames_after(CUE_AFTER, fps))})
    return planned


def speech_end(scene):
    ends = [track["start"] + track["duration"] for track in scene.get("voice_tracks") or []]
    ends += [line["start"] + line["duration"] for line in scene.get("lines") or [] if line.get("duration")]
    if scene.get("audio"):
        ends.append(scene.get("audio_offset", 0) + scene.get("audio_duration", 0))
    return max(ends) if ends else None


def hold_windows(manifest):
    """Absolute (start, end) seconds where a scene is meant to hold still after speaking."""
    windows = []
    for scene in manifest["scenes"]:
        start, duration = scene["start"], scene["duration"]
        spoken = speech_end(scene)
        local = spoken if spoken is not None else max(0, duration - scene.get("hold", 1))
        windows.append((round(start + min(local, duration), 6), round(start + duration, 6)))
    return windows


def mean_difference(first, second):
    return sum(abs(a - b) for a, b in zip(first, second)) / len(first)


def overlap(start, end, windows):
    return sum(max(0, min(end, b) - max(start, a)) for a, b in windows)


def inside(time, windows):
    return any(a <= time <= b for a, b in windows)


def motion_summary(samples, interval, duration, holds):
    """Summarize sampled gray frames taken ``interval`` seconds apart."""
    diffs = [mean_difference(samples[k - 1], samples[k]) for k in range(1, len(samples))]
    moving_share = sum(d > MOVING for d in diffs) / len(diffs) if diffs else 0
    runs, first = [], None
    for k, d in enumerate(diffs + [MOVING + 1], 1):
        if d <= MOVING and first is None:
            first = k - 1
        elif d > MOVING and first is not None:
            start, end = first * interval, (k - 1) * interval
            if end - start >= STATIC_SECONDS - 1e-9:
                outside = end - start - overlap(start, end, holds)
                runs.append({"start": round(start, 3), "end": round(end, 3), "seconds": round(end - start, 3),
                             "outside_holds": round(outside, 3), "flagged": outside >= STATIC_SECONDS - 1e-9})
            first = None
    cells = [round(i * CELL_SECONDS, 3) for i in range(math.ceil(duration / CELL_SECONDS) + 1)
             if i * CELL_SECONDS < duration - 0.05]
    pick = lambda t: samples[min(len(samples) - 1, round(t / interval))]
    pairs = [{"from": a, "to": b, "change": round(mean_difference(pick(a), pick(b)), 2)}
             for a, b in zip(cells, cells[1:])]
    flat = [p for p in pairs if p["change"] < FLAT and not inside(p["to"], holds)]
    average = sum(p["change"] for p in pairs) / len(pairs) if pairs else 0
    notes = []
    if any(run["flagged"] for run in runs):
        notes.append(f"static for {STATIC_SECONDS:g}+ s outside a hold: add a secondary action or a slow push-in, or declare the hold")
    if flat:
        notes.append(f"{len(flat)} cell pair(s) {CELL_SECONDS:g} s apart barely change outside holds: add a visible new element")
    if pairs and average < RICH and flat:
        notes.append(f"average cell change {average:.1f} is under {RICH} (upstream guidance for explainers)")
    return {"status": "advisory", "sample_seconds": interval, "moving_share": round(moving_share, 3),
            "average_cell_change": round(average, 2), "cell_pairs": pairs, "flat_cell_pairs": flat,
            "static_runs": runs, "holds": [list(w) for w in holds], "notes": notes,
            "thresholds": {"moving": MOVING, "flat": FLAT, "rich": RICH, "static_seconds": STATIC_SECONDS}}


def ffmpeg(arguments, **kwargs):
    result = subprocess.run(["ffmpeg", "-n", "-v", "error", *arguments], capture_output=True, **kwargs)
    if result.returncode:
        stderr = result.stderr if isinstance(result.stderr, str) else result.stderr.decode(errors="replace")
        raise ValueError(f"ffmpeg failed ({result.returncode}):\n{stderr[-4000:]}")
    return result.stdout


def select(frames):
    return "select='" + "+".join(f"eq(n\\,{n})" for n in frames) + "'"


def extract_frames(video, frames, out_dir, prefix):
    """Write each unique frame once; return frame -> PNG path."""
    unique = sorted(set(frames))
    ffmpeg(["-i", str(video), "-vf", select(unique), "-fps_mode", "passthrough", str(out_dir / f"{prefix}-%04d.png")])
    paths = {frame: out_dir / f"{prefix}-{i:04}.png" for i, frame in enumerate(unique, 1)}
    missing = [frame for frame, path in paths.items() if not path.is_file()]
    if missing:
        raise ValueError(f"could not extract review frames {missing[:5]} from {video}")
    return paths


def tile(images, columns, cell, out):
    rows = math.ceil(len(images) / columns)
    listing = out.with_suffix(".txt")
    listing.write_text("".join("file '" + str(p).replace("'", "'\\''") + "'\n" for p in images), encoding="utf-8")
    try:
        ffmpeg(["-f", "concat", "-safe", "0", "-i", str(listing), "-vf",
                f"scale={cell[0]}:{cell[1]},tile={columns}x{rows}:padding={SHEET_PADDING}:margin={SHEET_MARGIN}:color=white",
                "-frames:v", "1", str(out)])
    finally:
        listing.unlink(missing_ok=True)


def scan_sheets(video, fps, width, height, total_frames, out_dir):
    frames, columns, cell = scan_frames(total_frames, fps), scan_columns(width, height), cell_size(width, height)
    rows = SCAN_CELLS // columns
    ffmpeg(["-i", str(video), "-vf",
            f"select='not(mod(n\\,{max(1, round(fps / SCAN_PER_SECOND))}))',scale={cell[0]}:{cell[1]},"
            f"tile={columns}x{rows}:padding={SHEET_PADDING}:margin={SHEET_MARGIN}:color=white",
            "-fps_mode", "passthrough", str(out_dir / "scan-%02d.png")])
    sheets = []
    for i in range(0, len(frames), SCAN_CELLS):
        chunk = frames[i:i + SCAN_CELLS]
        name = f"scan-{i // SCAN_CELLS + 1:02}.png"
        if not (out_dir / name).is_file():
            raise ValueError(f"scan sheet was not written: {name}")
        sheets.append({"file": name, "cells": len(chunk), "columns": columns,
                       "first_seconds": round(chunk[0] / fps, 3), "last_seconds": round(chunk[-1] / fps, 3),
                       "step_seconds": round((frames[1] - frames[0]) / fps, 3) if len(frames) > 1 else 0})
    return sheets


def cue_sheets(video, manifest, fps, width, height, total_frames, out_dir, work):
    planned = cue_frames(manifest, fps, total_frames)
    if not planned:
        return []
    paths = extract_frames(video, [f for c in planned for f in (c["before_frame"], c["after_frame"])], work, "cue")
    sheets = []
    for i in range(0, len(planned), CUES_PER_SHEET):
        chunk = planned[i:i + CUES_PER_SHEET]
        name = f"cues-{i // CUES_PER_SHEET + 1:02}.png"
        tile([paths[f] for c in chunk for f in (c["before_frame"], c["after_frame"])], 4, cell_size(width, height), out_dir / name)
        sheets.append({"file": name, "cues": [{**c, "before_seconds": round(c["before_frame"] / fps, 3),
                                                "after_seconds": round(c["after_frame"] / fps, 3)} for c in chunk]})
    return sheets


def gray_samples(video, fps, width, height):
    lag = max(1, round(fps / MOTION_PER_SECOND))
    w, h = MOTION_WIDTH, even(MOTION_WIDTH * height / width)
    raw = ffmpeg(["-i", str(video), "-vf", f"select='not(mod(n\\,{lag}))',scale={w}:{h},format=gray",
                  "-fps_mode", "passthrough", "-f", "rawvideo", "-"])
    size = w * h
    return [raw[i:i + size] for i in range(0, len(raw) - size + 1, size)], lag / fps


def write_index(report, out_dir):
    lines = ["Review sheets (cells read left to right, top to bottom).", ""]
    for sheet in report["scan_sheets"]:
        lines.append(f"{sheet['file']}: {sheet['cells']} cells, {sheet['first_seconds']:.2f}–{sheet['last_seconds']:.2f} s, "
                     f"one every {sheet['step_seconds']:.3f} s, {sheet['columns']} per row")
    for sheet in report["cue_sheets"]:
        lines.append(f"{sheet['file']}: per row two cues, each as before ({CUE_BEFORE:g} s early) then after (+{CUE_AFTER:g} s)")
        for cue in sheet["cues"]:
            lines.append(f"  scene {cue['scene']} · {cue['cue']} at {cue['seconds']:.2f} s "
                         f"(before {cue['before_seconds']:.2f} s, after {cue['after_seconds']:.2f} s)")
    if not report["cue_sheets"]:
        lines.append("No explicit scene cues; no cue sheet.")
    lines.append(f"{report['phone_sheet']}: QA stills at {PHONE_WIDTH} px wide; anything a viewer must read should stay legible.")
    motion = report["motion"]
    lines += ["", f"Motion advisory: average cell change {motion['average_cell_change']}, "
              f"moving share {motion['moving_share']:.0%}; holds are exempt."]
    lines += [f"  - {note}" for note in motion["notes"]] or ["  - no flagged stretches"]
    (out_dir / "review.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_review(video, manifest, fps, width, height, total_frames, out_dir, stills):
    """Write sheets into ``out_dir`` and return the report section (file names are relative)."""
    out_dir = Path(out_dir)
    work = out_dir / ".frames"
    work.mkdir()
    try:
        report = {"scan_sheets": scan_sheets(video, fps, width, height, total_frames, out_dir),
                  "cue_sheets": cue_sheets(video, manifest, fps, width, height, total_frames, out_dir, work)}
        phone = (PHONE_WIDTH, even(PHONE_WIDTH * height / width))
        tile([Path(p) for p in stills], 1, phone, out_dir / "phone-width.png")
        report["phone_sheet"] = "phone-width.png"
        samples, interval = gray_samples(video, fps, width, height)
        report["motion"] = motion_summary(samples, interval, total_frames / fps, hold_windows(manifest))
    finally:
        for path in work.glob("*"):
            path.unlink()
        work.rmdir()
    write_index(report, out_dir)
    return report
