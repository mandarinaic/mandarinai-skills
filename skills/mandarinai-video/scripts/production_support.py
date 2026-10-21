"""Portable cast snapshots and narration-safe musical timing for video projects.

The cast is packaged with the skill; building a project never needs a checkout
of Swan. Beat boundaries are calculated on the global timeline, then rounded
up once to a video frame so non-divisor tempos do not accumulate drift.
"""

import copy
from fractions import Fraction
import json
import math
from pathlib import Path
import re


VOICE_ID = re.compile(r"[a-z]{2,3}-[A-Z]{2}-[A-Za-z][A-Za-z0-9]*Neural\Z")
CUE_ID = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,63}\Z")
SNAP_MODES = {"none", "beat", "bar"}


def _finite(value, label, low=0, high=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    if value < low or (high is not None and value > high):
        raise ValueError(f"{label} must be at least {low}" + (f" and at most {high}" if high is not None else ""))
    return value


def _fps(value):
    value = _finite(value, "fps")
    if value <= 0:
        raise ValueError("fps must be positive")
    return Fraction(str(value))


def _ceil(value):
    return -(-value.numerator // value.denominator)


def load_cast(config, assets_root):
    """Resolve an optional cast and explicit per-character voice overrides.

    ``None`` preserves projects with no cast. An object, including ``{}``,
    enables every companion so individual scenes can name their own speaker.
    Portraits remain portable filenames for the builder to copy into a project.
    """
    if config is None:
        return {"presenter": None, "characters": {}}
    if not isinstance(config, dict):
        raise ValueError("cast must be an object")
    if set(config) - {"presenter", "overrides"}:
        raise ValueError("cast accepts only presenter and overrides")
    snapshot_path = Path(assets_root) / "cast" / "characters.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    if snapshot.get("schema_version") != 1 or not isinstance(snapshot.get("characters"), list):
        raise ValueError("unsupported cast snapshot")
    characters = {profile["id"]: copy.deepcopy(profile) for profile in snapshot["characters"]}
    presenter = config.get("presenter")
    if presenter is not None and (not isinstance(presenter, str) or presenter not in characters):
        raise ValueError(f"unknown cast presenter: {presenter!r}")
    overrides = config.get("overrides", {})
    if not isinstance(overrides, dict):
        raise ValueError("cast overrides must be an object")
    for character_id, override in overrides.items():
        if character_id not in characters:
            raise ValueError(f"unknown cast override: {character_id!r}")
        if not isinstance(override, dict) or set(override) != {"voice"}:
            raise ValueError(f"cast override {character_id!r} must contain only voice")
        voice = override["voice"]
        if not isinstance(voice, str) or not VOICE_ID.fullmatch(voice):
            raise ValueError(f"invalid Neural voice for {character_id!r}")
        characters[character_id]["voice"] = voice
    return {"presenter": presenter, "characters": characters}


def resolve_speaker(cast, speaker):
    """Return a scene's named speaker, or its default presenter if omitted."""
    character_id = cast.get("presenter") if speaker is None else speaker
    if character_id is None:
        return None
    if not isinstance(character_id, str) or character_id not in cast.get("characters", {}):
        raise ValueError(f"unknown cast speaker: {character_id!r}")
    return cast["characters"][character_id]


def timing_config(value):
    """Validate a tempo configuration and expose its seconds-per-beat value."""
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("timing must be an object")
    if set(value) - {"bpm", "beats_per_bar", "snap", "offset"}:
        raise ValueError("timing accepts only bpm, beats_per_bar, snap, and offset")
    bpm = _finite(value.get("bpm"), "timing bpm", 20, 240)
    beats = value.get("beats_per_bar", 4)
    if isinstance(beats, bool) or not isinstance(beats, int) or not 1 <= beats <= 12:
        raise ValueError("timing beats_per_bar must be an integer from 1 to 12")
    snap = value.get("snap", "none")
    if not isinstance(snap, str) or snap not in SNAP_MODES:
        raise ValueError("timing snap must be none, beat, or bar")
    offset = _finite(value.get("offset", 0), "timing offset", 0, 10)
    return {"bpm": bpm, "beats_per_bar": beats, "snap": snap, "offset": offset, "seconds_per_beat": 60 / bpm}


def snap_end_frame(start_frame, minimum_seconds, fps, timing, snap=None):
    """Find the first global beat/bar boundary after a scene's minimum end.

    Minimum seconds must already include narration and any reading or response
    hold. Rounding always goes forward, so no speech or hold can be cut short.
    ``snap='none'`` may override a project's default snap for a specific scene.
    """
    if isinstance(start_frame, bool) or not isinstance(start_frame, int) or start_frame < 0:
        raise ValueError("start_frame must be a nonnegative integer")
    minimum_seconds = _finite(minimum_seconds, "minimum_seconds")
    frame_rate = _fps(fps)
    mode = snap if snap is not None else timing.get("snap", "none") if timing else "none"
    if not isinstance(mode, str) or mode not in SNAP_MODES:
        raise ValueError("snap must be none, beat, or bar")
    end = Fraction(start_frame, 1) / frame_rate + Fraction(str(minimum_seconds))
    if mode != "none":
        if timing is None:
            raise ValueError("beat and bar snapping require timing bpm")
        period = Fraction(60, 1) / Fraction(str(timing["bpm"]))
        if mode == "bar":
            period *= timing["beats_per_bar"]
        offset = Fraction(str(timing["offset"]))
        boundary = max(0, _ceil((end - offset) / period))
        end = offset + boundary * period
    return _ceil(end * frame_rate)


def cue_times(cues, duration, fps, timing):
    """Resolve named, scene-relative cues to actual video-frame timestamps.

    A cue declares exactly one of ``seconds`` or zero-based ``beat``. Global
    timing offset affects scene boundaries only, never a scene-relative cue.
    """
    if not isinstance(cues, list):
        raise ValueError("cues must be a list")
    duration = _finite(duration, "cue duration")
    frame_rate = _fps(fps)
    frames = _ceil(Fraction(str(duration)) * frame_rate)
    resolved = {}
    for cue in cues:
        if not isinstance(cue, dict):
            raise ValueError("each cue must be an object")
        if set(cue) - {"id", "seconds", "beat"}:
            raise ValueError("cues accept only id and seconds or beat")
        cue_id = cue.get("id")
        if not isinstance(cue_id, str) or not CUE_ID.fullmatch(cue_id):
            raise ValueError("cue id must start with a letter and contain letters, numbers, underscores, or hyphens")
        if cue_id in resolved:
            raise ValueError(f"duplicate cue id: {cue_id!r}")
        if ("seconds" in cue) == ("beat" in cue):
            raise ValueError(f"cue {cue_id!r} requires exactly one of seconds or beat")
        if "beat" in cue:
            beat = _finite(cue["beat"], f"cue {cue_id!r} beat")
            if timing is None:
                raise ValueError(f"cue {cue_id!r} beat requires timing bpm")
            seconds = Fraction(str(beat)) * Fraction(60, 1) / Fraction(str(timing["bpm"]))
        else:
            seconds = Fraction(str(_finite(cue["seconds"], f"cue {cue_id!r} seconds")))
        frame = _ceil(seconds * frame_rate)
        if frame >= frames:
            raise ValueError(f"cue {cue_id!r} falls outside the scene")
        resolved[cue_id] = {"seconds": float(Fraction(frame, 1) / frame_rate), "frame": frame}
        if "beat" in cue:
            resolved[cue_id]["beat"] = cue["beat"]
    return resolved
