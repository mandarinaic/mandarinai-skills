#!/usr/bin/env python3
"""Make a quiet, original beat-aligned WAV bed without samples or services.

The fixed recipe uses a Cmaj7 / Am7 / Fmaj7 / G7 arpeggio and soft bass
pulses. It provides declared-tempo music, not beat detection or time-stretching
for other recordings. Only the Python standard library is required.
"""

import argparse
from array import array
import json
import math
from pathlib import Path
import sys
import wave


RECIPE = "mandarinai-warm-sevenths-v1"
CHORDS = (
    ("Cmaj7", (60, 64, 67, 71), 36),
    ("Am7", (57, 60, 64, 67), 33),
    ("Fmaj7", (53, 57, 60, 64), 29),
    ("G7", (55, 59, 62, 65), 31),
)


def finite(value, name, low, high):
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or not low <= value <= high):
        raise ValueError(f"{name} must be finite and between {low} and {high}")


def integer(value, name, low, high):
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ValueError(f"{name} must be an integer from {low} to {high}")


def validate(bpm, bars, beats_per_bar, sample_rate, gain):
    finite(bpm, "bpm", 20, 240)
    integer(bars, "bars", 1, 128)
    integer(beats_per_bar, "beats-per-bar", 1, 12)
    integer(sample_rate, "sample-rate", 8000, 96000)
    finite(gain, "gain", 0, 1)
    if gain == 0:
        raise ValueError("gain must be greater than zero")
    duration = bars * beats_per_bar * 60 / bpm
    if duration > 600:
        raise ValueError("music bed must be at most 10 minutes; reduce bars or beats-per-bar")
    return duration, round(duration * sample_rate)


def add_pluck(buffer, offset, count, midi, sample_rate, amplitude, pan, bass=False):
    """Add one gently attacked, decaying note to an interleaved stereo bar."""
    count = min(count, len(buffer) // 2 - offset)
    if count <= 0:
        return
    omega = math.tau * 440 * 2 ** ((midi - 69) / 12) / sample_rate
    attack = max(1, round(sample_rate * (0.018 if bass else 0.012)))
    release = max(1, round(sample_rate * 0.06))
    decay = math.exp(-4.5 / count)
    envelope = 1.0
    left, right = math.sqrt((1 - pan) / 2), math.sqrt((1 + pan) / 2)
    # Bound each voice's sum of harmonics before panning, even at gain=1.
    scale = amplitude / (1.12 if bass else 1.20)
    for i in range(count):
        phase = omega * i
        tone = math.sin(phase) + (0.12 if bass else 0.16) * math.sin(phase * 2)
        if not bass:
            tone += 0.04 * math.sin(phase * 3)
        edge = min(1, i / attack) * min(1, (count - 1 - i) / release)
        value = tone * scale * envelope * edge
        frame = (offset + i) * 2
        buffer[frame] += value * left
        buffer[frame + 1] += value * right
        envelope *= decay


def write_music(destination, bpm, bars, beats_per_bar, sample_rate, gain, sample_count):
    """Stream one bar at a time so the ten-minute limit does not require huge RAM."""
    beat_samples = sample_rate * 60 / bpm
    head_fade = max(1, min(round(sample_rate * 0.1), sample_count // 4))
    tail_fade = max(1, min(round(sample_rate * 0.18), sample_count // 4))
    with wave.open(destination, "wb") as audio:
        audio.setnchannels(2)
        audio.setsampwidth(2)
        audio.setframerate(sample_rate)
        audio.setnframes(sample_count)
        for bar in range(bars):
            start = round(bar * beats_per_bar * beat_samples)
            end = sample_count if bar == bars - 1 else round((bar + 1) * beats_per_bar * beat_samples)
            frames = end - start
            buffer = array("f", [0]) * (frames * 2)
            _, chord, root = CHORDS[bar % len(CHORDS)]
            for beat in range(beats_per_bar):
                offset = round((bar * beats_per_bar + beat) * beat_samples) - start
                midi = chord[(0, 2, 1, 3)[beat % 4]]
                accent = (0.96, 0.72, 0.82, 0.72)[beat % 4]
                add_pluck(buffer, offset, round(min(0.95 * sample_rate, beat_samples * 0.72)),
                          midi, sample_rate, 0.66 * accent, (-0.18, 0.18)[beat % 2])
                if beat % 2 == 0:
                    add_pluck(buffer, offset, round(min(0.25 * sample_rate, beat_samples * 0.4)),
                              root, sample_rate, 0.28, 0, bass=True)
            pcm = array("h")
            for frame in range(frames):
                position = start + frame
                fade = min(1, position / head_fade, (sample_count - 1 - position) / tail_fade)
                for channel in (0, 1):
                    # The recipe peaks below full scale; limiting also protects future recipes.
                    value = round(buffer[frame * 2 + channel] * gain * fade * 32767)
                    pcm.append(max(-32767, min(32767, value)))
            if sys.byteorder != "little":
                pcm.byteswap()
            audio.writeframesraw(pcm.tobytes())


def make_music(*, bpm, bars, beats_per_bar=4, out, sample_rate=48000, gain=0.25):
    duration, sample_count = validate(bpm, bars, beats_per_bar, sample_rate, gain)
    output = Path(out).expanduser().absolute()
    if output.suffix.lower() != ".wav":
        raise ValueError("--out must end in .wav")
    metadata_path = output.with_suffix(".music.json")
    for path in (output, metadata_path):
        if path.exists() or path.is_symlink():
            raise ValueError(f"output already exists: {path}; choose a new output name")
    output.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "schema_version": 1,
        "bpm": bpm,
        "beats_per_bar": beats_per_bar,
        "bars": bars,
        "duration": sample_count / sample_rate,
        "requested_duration": duration,
        "sample_count": sample_count,
        "sample_rate": sample_rate,
        "bit_depth": 16,
        "channels": 2,
        "gain": gain,
        "original_synthesized": True,
        "sampled_assets": False,
        "recipe": RECIPE,
        "progression": [chord[0] for chord in CHORDS],
        "timing_note": "Declared BPM and beat-aligned synthesis; no beat detection or time-stretch of other files.",
    }
    created = []
    try:
        # Exclusive creation prevents both accidental overwrites and check/create races.
        with output.open("xb") as destination:
            created.append(output)
            with metadata_path.open("x", encoding="utf-8") as metadata_file:
                created.append(metadata_path)
                write_music(destination, bpm, bars, beats_per_bar, sample_rate, gain, sample_count)
                json.dump(metadata, metadata_file, indent=2, ensure_ascii=False, allow_nan=False)
                metadata_file.write("\n")
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        raise
    return output, metadata_path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bpm", required=True, type=float, help="Declared tempo, 20–240 BPM")
    parser.add_argument("--bars", required=True, type=int, help="Length, 1–128 bars, at most ten minutes")
    parser.add_argument("--beats-per-bar", type=int, default=4, help="Beats in each bar, 1–12 (default: 4)")
    parser.add_argument("--out", required=True, help="New WAV path; adjacent .music.json must also be new")
    parser.add_argument("--sample-rate", type=int, default=48000, help="8000–96000 Hz (default: 48000)")
    parser.add_argument("--gain", type=float, default=0.25, help="Master gain, greater than 0 and at most 1")
    args = parser.parse_args(argv)
    try:
        output, metadata = make_music(**vars(args))
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(f"Music: {output}\nMetadata: {metadata}")


if __name__ == "__main__":
    main()
