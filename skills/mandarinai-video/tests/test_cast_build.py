"""Independent end-to-end builder checks for cast audio and musical timing.

Everything is generated in temporary directories. Narration requests are
replaced with real WAV files, so ffprobe still measures the resulting audio.
"""

import argparse
import contextlib
import copy
from fractions import Fraction
import importlib.util
import io
import json
import math
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock
import wave


SKILL = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), SKILL / "scripts" / f"{name}.py")
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


BUILD = module("build-project")
RENDER = module("render-project")
HAS_FFPROBE = bool(shutil.which("ffprobe"))


def ceil_fraction(value):
    return -(-value.numerator // value.denominator)


class CastBuildCase(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="mandarinai-cast-build-")
        self.addCleanup(temporary.cleanup)
        self.work = Path(temporary.name).resolve()
        self.serial = 0
        self.source = self.work / "source.json"
        self.source.write_text(json.dumps({
            "kind": "grammar", "id": "4", "title": "能", "language": "en",
            "url": "https://www.mandarinai.com/grammar/detail/4", "content": {},
        }, ensure_ascii=False), encoding="utf-8")

    def brief(self, scenes, **fields):
        return {"source": "source.json", "mode": "tutorial", "fps": 30, "scenes": scenes, **fields}

    def args(self, brief, *, tts=False, silent=False):
        self.serial += 1
        path = self.work / f"brief-{self.serial}.json"
        path.write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
        return argparse.Namespace(
            brief=str(path), out=str(self.work / f"project-{self.serial}"), source=None,
            tts=tts, silent=silent, voice="en-US-AriaNeural", tts_url="https://tts.invalid/tts",
        )

    def build(self, brief, *, tts=False, silent=False, generated_seconds=None):
        args = self.args(brief, tts=tts, silent=silent)
        durations = iter(generated_seconds or [])

        def generate(text, voice, url, path):
            self.wave(path, next(durations))

        with mock.patch.object(BUILD, "fetch_tts", side_effect=generate if tts else AssertionError("unexpected network request")) as fetch:
            with contextlib.redirect_stdout(io.StringIO()):
                BUILD.build(args)
        project = Path(args.out)
        return project, json.loads((project / "project.json").read_text(encoding="utf-8")), fetch

    def wave(self, path, seconds):
        rate = 16000
        frames = round(seconds * rate)
        with wave.open(str(path), "wb") as recording:
            recording.setnchannels(1)
            recording.setsampwidth(2)
            recording.setframerate(rate)
            recording.writeframes(b"\0\0" * frames)
        return frames / rate

    def payload(self, project, scene):
        markup = (project / scene["file"]).read_text(encoding="utf-8")
        return json.JSONDecoder().raw_decode(markup.split("const DATA=", 1)[1])[0], markup

    def validated(self, project, manifest):
        result = copy.deepcopy(manifest)
        RENDER.validate(project, result)
        return result


class SilentCastBuildTests(CastBuildCase):
    def test_silent_dialogue_keeps_estimated_lines_and_marks_pending(self):
        project, manifest, fetch = self.build(self.brief([{
            "layout": "lesson", "heading": "Can you come?", "duration": 0.2, "hold": 0.7,
            "lines": [
                {"speaker": "yue", "text": "你能来吗？", "pinyin": "nǐ néng lái ma", "translation": "Can you come?", "pause_after": 0.45},
                {"speaker": "maya", "text": "我能来。", "pinyin": "wǒ néng lái", "translation": "I can come."},
            ],
        }], timing={"bpm": 137, "snap": "beat"}), silent=True)
        fetch.assert_not_called()
        scene = manifest["scenes"][0]
        self.assertEqual(manifest["audio_mode"], "silent")
        self.assertTrue(manifest["pending_narration"])
        self.assertTrue(scene["pending_narration"])
        self.assertEqual(scene["voice_tracks"], [])
        self.assertIsNone(scene["audio"])
        self.assertEqual([line["speaker"] for line in scene["lines"]], ["yue", "maya"])
        for line in scene["lines"]:
            self.assertEqual(line["timing_method"], "estimated")
            self.assertGreater(line["duration"], 0)
            self.assertIsNone(line["audio"])
        first, second = scene["lines"]
        self.assertAlmostEqual(second["start"], first["start"] + first["duration"] + 0.45)
        self.assertGreaterEqual(scene["duration"] + 1e-9, second["start"] + second["duration"] + 0.7)
        self.assertFalse(any(path.suffix.lower() in {".wav", ".mp3"} for path in project.rglob("*")))
        subtitles = (project / "captions.srt").read_text(encoding="utf-8").strip().split("\n\n")
        self.assertEqual(len(subtitles), 2)
        self.assertEqual([entry.splitlines()[2] for entry in subtitles], ["你能来吗？", "我能来。"])
        self.assertIn("PENDING", (project / "script.md").read_text(encoding="utf-8"))
        self.assertFalse(self.validated(project, manifest)["scenes"][0]["resolved_voice_tracks"])

    def test_invalid_dialogue_is_rejected_before_any_tts_or_output(self):
        valid = {"layout": "lesson", "heading": "First", "speaker": "yue", "narration": "你好。"}
        invalid = [
            {"layout": "lesson", "heading": "Mixed", "narration": "不能混用。", "lines": [{"speaker": "maya", "text": "你好。"}]},
            {"layout": "lesson", "heading": "Unknown", "lines": [{"speaker": "invented", "text": "你好。"}]},
            {"layout": "lesson", "heading": "Unknown", "speaker": "invented", "narration": "你好。"},
            {"layout": "lesson", "heading": "Unnamed", "lines": [{"text": "你好。"}]},
        ]
        for scene in invalid:
            with self.subTest(scene=scene):
                args = self.args(self.brief([valid, scene]), tts=True)
                with mock.patch.object(BUILD, "fetch_tts", side_effect=AssertionError("must validate before requesting narration")) as fetch:
                    with self.assertRaises(ValueError):
                        BUILD.build(args)
                fetch.assert_not_called()
                self.assertFalse(Path(args.out).exists())

    def test_global_non_divisor_tempo_uses_absolute_frame_ceiling(self):
        scenes = [{"layout": "lesson", "heading": f"Beat {index}", "duration": 0.12} for index in range(24)]
        for fps in [24, 30]:
            with self.subTest(fps=fps):
                _, manifest, fetch = self.build(self.brief(scenes, fps=fps, timing={"bpm": 137, "snap": "beat"}))
                fetch.assert_not_called()
                previous = 0
                for index, scene in enumerate(manifest["scenes"], 1):
                    absolute_end = ceil_fraction(Fraction(index * 60 * fps, 137))
                    self.assertEqual(scene["frames"], absolute_end - previous)
                    self.assertEqual(scene["start"], previous / fps)
                    self.assertEqual(scene["duration"], scene["frames"] / fps)
                    previous = absolute_end
                self.assertEqual(manifest["frames"], ceil_fraction(Fraction(24 * 60 * fps, 137)))

    def test_legacy_scene_timing_and_no_cast_still_build(self):
        project, manifest, fetch = self.build(self.brief([
            {"layout": "lesson", "heading": "Learn", "text": "能", "duration": 1.01},
            {"layout": "cta", "heading": "Practice", "duration": 1.51},
        ], fps=24))
        fetch.assert_not_called()
        self.assertEqual(manifest["cast"], {"presenter": None, "characters": {}})
        self.assertIsNone(manifest["timing"])
        self.assertEqual(manifest["frames"], 62)
        self.assertEqual([scene["frames"] for scene in manifest["scenes"]], [25, 37])
        for scene in manifest["scenes"]:
            self.assertNotIn("voice_tracks", scene)
            self.assertEqual(scene["lines"], [])
            self.assertIsNone(scene["speaker"])
        self.validated(project, manifest)


@unittest.skipUnless(HAS_FFPROBE, "ffprobe is required to measure generated WAV narration")
class MeasuredCastBuildTests(CastBuildCase):
    def test_presenter_stays_consistent_in_voice_portraits_payload_and_mix(self):
        project, manifest, fetch = self.build(self.brief([
            {"layout": "hero", "heading": "Ability", "narration": "能表示能力。", "duration": 0.3},
            {"layout": "lesson", "heading": "Practice", "narration": "我能说中文。", "duration": 0.3},
        ], cast={"presenter": "jin"}), tts=True, generated_seconds=[1.11, 0.77])
        self.assertEqual([call.args[1] for call in fetch.call_args_list], ["zh-CN-YunyangNeural"] * 2)
        self.assertEqual(manifest["cast"]["presenter"], "jin")
        self.assertEqual(manifest["audio_mode"], "narrated")
        for profile in manifest["cast"]["characters"].values():
            self.assertEqual(profile["portrait"], f"assets/cast/{profile['id']}-calm.webp")
            self.assertTrue((project / profile["portrait"]).is_file())
        for scene in manifest["scenes"]:
            self.assertEqual(scene["speaker"], "jin")
            self.assertEqual(len(scene["voice_tracks"]), 1)
            track = scene["voice_tracks"][0]
            self.assertEqual((track["speaker"], track["voice"], track["source"]), ("jin", "zh-CN-YunyangNeural", "tts"))
            self.assertEqual(scene["audio"], track["file"])
            payload, markup = self.payload(project, scene)
            self.assertEqual(payload["presenter"]["id"], "jin")
            self.assertEqual(payload["presenter"]["role"], "Grammar & Culture Mentor")
            self.assertEqual(payload["cast"]["jin"]["voice"], "zh-CN-YunyangNeural")
            self.assertEqual(payload["voice_tracks"], scene["voice_tracks"])
            self.assertIn('src="../assets/cast/jin-calm.webp"', markup)
            self.assertNotIn(str(self.work), json.dumps(payload))
        validated = self.validated(project, manifest)
        self.assertEqual([len(scene["resolved_voice_tracks"]) for scene in validated["scenes"]], [1, 1])
        command = RENDER.audio_mix_command(self.work / "joined.mp4", self.work / "final.mp4", validated, manifest["duration"])
        self.assertEqual(command.count("-i"), 3)
        for scene in validated["scenes"]:
            self.assertEqual(command.count(str(scene["resolved_voice_tracks"][0]["path"])), 1)

    def test_dialogue_measures_ordered_utterances_holds_cues_and_global_grid(self):
        durations = [1.137, 0.813]
        for audio_source in ["tts", "local"]:
            with self.subTest(audio_source=audio_source):
                first = {"speaker": "yue", "text": "你能来吗？", "pinyin": "nǐ néng lái ma", "translation": "Can you come?", "pause_after": 0.27}
                second = {"speaker": "maya", "text": "我能来。", "pinyin": "wǒ néng lái", "translation": "I can come.", "pause_after": 0.4}
                if audio_source == "local":
                    for index, line in enumerate([first, second]):
                        path = self.work / f"local-{index}.wav"
                        self.wave(path, durations[index])
                        line["audio"] = path.name
                project, manifest, fetch = self.build(self.brief([
                    {"layout": "hero", "heading": "Modal verb", "duration": 0.6},
                    {"layout": "lesson", "heading": "Can you come?", "duration": 0.3, "hold": 1.04,
                     "lines": [first, second], "cues": [{"id": "modal", "beat": 1}, {"id": "prompt", "seconds": 1.01}]},
                ], timing={"bpm": 137, "snap": "beat"}), tts=audio_source == "tts", generated_seconds=durations)
                if audio_source == "tts":
                    self.assertEqual([call.args[1] for call in fetch.call_args_list], ["zh-CN-XiaoxuanNeural", "zh-CN-XiaoyiNeural"])
                else:
                    fetch.assert_not_called()
                intro, scene = manifest["scenes"]
                tracks = scene["voice_tracks"]
                self.assertEqual([track["speaker"] for track in tracks], ["yue", "maya"])
                self.assertEqual([track["source"] for track in tracks], [audio_source, audio_source])
                self.assertEqual([track["voice"] for track in tracks], ["zh-CN-XiaoxuanNeural", "zh-CN-XiaoyiNeural"] if audio_source == "tts" else [None, None])
                self.assertAlmostEqual(tracks[0]["duration"], durations[0], places=5)
                self.assertAlmostEqual(tracks[1]["duration"], durations[1], places=5)
                self.assertEqual(tracks[0]["start"], 0.5)
                self.assertAlmostEqual(tracks[1]["start"], 0.5 + durations[0] + 0.27)
                minimum = 0.5 + durations[0] + 0.27 + durations[1] + 0.4 + 1.04
                self.assertAlmostEqual(scene["minimum_duration"], minimum)
                self.assertGreaterEqual(scene["duration"] + 1e-9, minimum)
                expected_beat = math.ceil((Fraction(intro["frames"], 30) + Fraction(str(minimum))) / Fraction(60, 137))
                expected_end = ceil_fraction(expected_beat * Fraction(60 * 30, 137))
                self.assertEqual(manifest["frames"], expected_end)
                self.assertEqual(scene["start"], intro["duration"])
                self.assertEqual(scene["cues"]["modal"], {"seconds": 14 / 30, "frame": 14, "beat": 1})
                self.assertEqual(scene["cues"]["prompt"], {"seconds": 31 / 30, "frame": 31})
                self.assertIsNone(scene["audio"])
                self.assertEqual([line["timing_method"] for line in scene["lines"]], ["measured", "measured"])
                self.assertEqual([line["audio"] for line in scene["lines"]], [track["file"] for track in tracks])
                payload, markup = self.payload(project, scene)
                self.assertEqual(payload["lines"], scene["lines"])
                self.assertEqual(payload["voice_tracks"], tracks)
                self.assertIn('data-speaker="yue"', markup)
                self.assertIn('data-speaker="maya"', markup)
                self.assertIn("<rt>néng</rt>", markup)
                subtitles = (project / "captions.srt").read_text(encoding="utf-8").strip().split("\n\n")
                self.assertEqual(len(subtitles), 2)
                for index, track in enumerate(tracks):
                    entry = subtitles[index].splitlines()
                    start = scene["start"] + track["start"]
                    self.assertEqual(entry[1], f"{BUILD.srt_time(start)} --> {BUILD.srt_time(start + track['duration'])}")
                    self.assertEqual(entry[2], ["你能来吗？", "我能来。"][index])
                validated = self.validated(project, manifest)
                self.assertEqual(len(validated["scenes"][1]["resolved_voice_tracks"]), 2)

    def test_legacy_local_audio_keeps_single_audio_compatibility(self):
        recording = self.work / "legacy.wav"
        seconds = self.wave(recording, 0.823)
        project, manifest, fetch = self.build(self.brief([
            {"layout": "lesson", "heading": "Legacy", "narration": "我能来。", "audio": recording.name, "duration": 0.41, "hold": 0.32},
        ], fps=24))
        fetch.assert_not_called()
        scene = manifest["scenes"][0]
        self.assertNotIn("voice_tracks", scene)
        self.assertEqual(scene["audio_duration"], seconds)
        self.assertEqual(scene["audio_offset"], 0.5)
        self.assertEqual(scene["frames"], math.ceil((0.5 + seconds + 0.32) * 24))
        self.assertEqual((project / scene["audio"]).read_bytes(), recording.read_bytes())
        validated = self.validated(project, manifest)
        self.assertEqual(len(validated["scenes"][0]["resolved_voice_tracks"]), 1)


if __name__ == "__main__":
    unittest.main()
