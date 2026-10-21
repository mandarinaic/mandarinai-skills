"""Offline cast parity and frame-accurate musical timing regression checks."""

from fractions import Fraction
import importlib.util
import json
from pathlib import Path
import unittest


SKILL = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("production_support", SKILL / "scripts" / "production_support.py")
SUPPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SUPPORT)

# Deliberate fixture from Swan useVoiceCasting.ts and useWordVideoGenerator.ts.
# Unit tests remain portable and do not require the private frontend checkout.
SWAN_CAST = {
    "yue": (22, "female", "Mandarin Learning Guide", "zh-CN-XiaoxuanNeural"),
    "jin": (58, "male", "Grammar & Culture Mentor", "zh-CN-YunyangNeural"),
    "lian": (26, "female", "Foodie & Culture Guide", "zh-CN-XiaoxiaoNeural"),
    "bai": (18, "male", "AI Mandarin Learning Genius", "zh-CN-YunxiNeural"),
    "maya": (16, "female", "Beginner Mandarin Learner", "zh-CN-XiaoyiNeural"),
    "amir": (24, "male", "Young Arab Professional Mandarin Learner", "zh-CN-YunxiNeural"),
    "grace": (63, "female", "Lifelong Mandarin Learner", "zh-CN-XiaoxiaoNeural"),
}
SWAN_VOICES = {
    "zh-CN-XiaoxiaoNeural": ("female", 26),
    "zh-CN-YunxiNeural": ("male", 24),
    "zh-CN-YunyangNeural": ("male", 42),
    "zh-CN-XiaoxuanNeural": ("female", 22),
    "zh-CN-XiaoyiNeural": ("female", 20),
    "zh-CN-YunxiaNeural": ("male", 10),
}


def ceil_fraction(value):
    return -(-value.numerator // value.denominator)


class CastTests(unittest.TestCase):
    def test_packaged_companions_match_swan_roles_and_casting(self):
        cast = SUPPORT.load_cast({}, SKILL / "assets")
        self.assertIsNone(cast["presenter"])
        self.assertEqual(set(cast["characters"]), set(SWAN_CAST))
        for character_id, (age, gender, role, voice) in SWAN_CAST.items():
            with self.subTest(character=character_id):
                profile = cast["characters"][character_id]
                self.assertEqual((profile["age"], profile["gender"], profile["role"], profile["voice"]), (age, gender, role, voice))
                candidates = [voice_id for voice_id, (voice_gender, voice_age) in SWAN_VOICES.items() if voice_gender == gender and voice_age >= 14]
                nearest = min(candidates, key=lambda voice_id: (abs(SWAN_VOICES[voice_id][1] - age), voice_id))
                self.assertEqual(profile["voice"], nearest)
                self.assertEqual(SWAN_VOICES[voice][0], gender)
                self.assertGreaterEqual(SWAN_VOICES[voice][1], 14)
                self.assertTrue(profile["traits"])
                self.assertEqual(profile["tier"], "guide" if character_id in {"yue", "jin", "lian", "bai"} else "learner")
                portrait = SKILL / "assets" / "cast" / profile["portrait"]
                self.assertEqual(portrait.name, f"{character_id}-calm.webp")
                data = portrait.read_bytes()
                self.assertEqual(data[:4], b"RIFF")
                self.assertEqual(data[8:12], b"WEBP")
                self.assertGreater(len(data), 1000)

    def test_source_provenance_is_portable(self):
        snapshot = json.loads((SKILL / "assets" / "cast" / "characters.json").read_text(encoding="utf-8"))
        self.assertEqual(snapshot["schema_version"], 1)
        self.assertEqual(snapshot["source"]["profiles"], "utils/characters.ts")
        self.assertEqual(snapshot["source"]["casting"], "composables/useVoiceCasting.ts")
        self.assertRegex(snapshot["source"]["revision"], r"^[0-9a-f]{40}$")
        self.assertNotIn("/Users/", json.dumps(snapshot))

    def test_optional_presenter_and_explicit_speaker(self):
        no_cast = SUPPORT.load_cast(None, SKILL / "assets")
        self.assertEqual(no_cast, {"presenter": None, "characters": {}})
        self.assertIsNone(SUPPORT.resolve_speaker(no_cast, None))
        cast = SUPPORT.load_cast({"presenter": "jin"}, SKILL / "assets")
        self.assertEqual(SUPPORT.resolve_speaker(cast, None)["id"], "jin")
        self.assertEqual(SUPPORT.resolve_speaker(cast, "yue")["voice"], "zh-CN-XiaoxuanNeural")
        self.assertEqual(SUPPORT.resolve_speaker(cast, "bai")["voice"], "zh-CN-YunxiNeural")
        with self.assertRaisesRegex(ValueError, "unknown cast speaker"):
            SUPPORT.resolve_speaker(cast, "invented")
        with self.assertRaisesRegex(ValueError, "unknown cast speaker"):
            SUPPORT.resolve_speaker(no_cast, "jin")

    def test_voice_override_is_explicit_and_does_not_mutate_snapshot(self):
        cast = SUPPORT.load_cast({"presenter": "jin", "overrides": {"jin": {"voice": "zh-CN-YunjianNeural"}}}, SKILL / "assets")
        self.assertEqual(SUPPORT.resolve_speaker(cast, None)["voice"], "zh-CN-YunjianNeural")
        self.assertEqual(SUPPORT.load_cast({}, SKILL / "assets")["characters"]["jin"]["voice"], "zh-CN-YunyangNeural")

    def test_invalid_cast_fails_before_generating_media(self):
        for config in [[], "jin", {"presenter": "rat"}, {"presenter": []}, {"unknown": True}, {"overrides": []}, {"overrides": {"unknown": {"voice": "zh-CN-YunxiNeural"}}}, {"overrides": {"jin": {}}}, {"overrides": {"jin": {"portrait": "another.webp"}}}, {"overrides": {"jin": {"voice": "https://example.invalid/voice"}}}, {"overrides": {"jin": {"voice": "zh-CN-YunyangNeural\n"}}}, {"overrides": {"jin": {"voice": True}}}]:
            with self.subTest(config=config), self.assertRaises(ValueError):
                SUPPORT.load_cast(config, SKILL / "assets")


class TimingTests(unittest.TestCase):
    def test_timing_defaults_and_validation(self):
        self.assertIsNone(SUPPORT.timing_config(None))
        self.assertEqual(SUPPORT.timing_config({"bpm": 120}), {"bpm": 120, "beats_per_bar": 4, "snap": "none", "offset": 0, "seconds_per_beat": 0.5})
        for config in [[], {}, {"bpm": True}, {"bpm": float("nan")}, {"bpm": float("inf")}, {"bpm": 19.9}, {"bpm": 241}, {"bpm": 120, "beats_per_bar": True}, {"bpm": 120, "beats_per_bar": 1.5}, {"bpm": 120, "beats_per_bar": 13}, {"bpm": 120, "snap": "unknown"}, {"bpm": 120, "snap": []}, {"bpm": 120, "offset": -1}, {"bpm": 120, "offset": float("inf")}, {"bpm": 120, "unknown": 2}]:
            with self.subTest(config=config), self.assertRaises(ValueError):
                SUPPORT.timing_config(config)

    def test_scene_end_never_truncates_narration_or_hold(self):
        for bpm in [20, 90, 120, 137, 173, 240]:
            for fps in [24, 30, 60]:
                for snap in ["none", "beat", "bar"]:
                    with self.subTest(bpm=bpm, fps=fps, snap=snap):
                        timing = SUPPORT.timing_config({"bpm": bpm, "snap": snap, "offset": 0.17})
                        start = 0
                        for i in range(100):
                            audio = 0.65 + (i % 7) * 0.187
                            hold = 0.8 + (i % 3) * 0.15
                            minimum = audio + hold
                            end = SUPPORT.snap_end_frame(start, minimum, fps, timing)
                            minimum_end = Fraction(start, fps) + Fraction(str(minimum))
                            self.assertGreaterEqual(Fraction(end, fps), minimum_end)
                            if snap != "none":
                                period = Fraction(60, bpm) * (4 if snap == "bar" else 1)
                                offset = Fraction(17, 100)
                                boundary = max(0, ceil_fraction((minimum_end - offset) / period))
                                expected = ceil_fraction((offset + boundary * period) * fps)
                                self.assertEqual(end, expected)
                            start = end

    def test_global_beat_grid_does_not_accumulate_frame_rounding_drift(self):
        for bpm in [90, 120, 137, 173]:
            for fps in [24, 30, 60]:
                for snap in ["beat", "bar"]:
                    with self.subTest(bpm=bpm, fps=fps, snap=snap):
                        timing = SUPPORT.timing_config({"bpm": bpm, "snap": snap})
                        start = 0
                        period = Fraction(60, bpm) * (4 if snap == "bar" else 1)
                        for scene_index in range(1, 101):
                            start = SUPPORT.snap_end_frame(start, 0.12, fps, timing)
                            # Each short scene consumes exactly one global unit;
                            # no per-scene ceil(period*fps) accumulation is allowed.
                            self.assertEqual(start, ceil_fraction(scene_index * period * fps))

    def test_snap_override_and_unaligned_end(self):
        timing = SUPPORT.timing_config({"bpm": 120, "snap": "bar", "offset": 0.25})
        self.assertEqual(SUPPORT.snap_end_frame(0, 1, 30, timing), 68)
        self.assertEqual(SUPPORT.snap_end_frame(0, 1, 30, timing, "beat"), 38)
        self.assertEqual(SUPPORT.snap_end_frame(0, 1.01, 30, timing, "none"), 31)
        self.assertEqual(SUPPORT.snap_end_frame(30, 1.01, 30, None), 61)
        self.assertEqual(SUPPORT.snap_end_frame(0, 1, 30, SUPPORT.timing_config({"bpm": 120, "snap": "beat"})), 30)
        for args in [(0, 1, 30, None, "beat"), (0, 1, 30, timing, "wrong"), (-1, 1, 30, timing), (True, 1, 30, timing), (0, -1, 30, timing), (0, float("inf"), 30, timing), (0, 1, 0, timing), (0, 1, True, timing)]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                SUPPORT.snap_end_frame(*args)

    def test_cues_are_frame_quantized_and_scene_relative(self):
        timing = SUPPORT.timing_config({"bpm": 137, "offset": 0.25})
        cues = SUPPORT.cue_times([{"id": "start", "beat": 0}, {"id": "modal", "beat": 1}, {"id": "prompt", "seconds": 1.01}], 3, 30, timing)
        self.assertEqual(cues["start"], {"seconds": 0, "frame": 0, "beat": 0})
        self.assertEqual(cues["modal"], {"seconds": 14 / 30, "frame": 14, "beat": 1})
        self.assertEqual(cues["prompt"], {"seconds": 31 / 30, "frame": 31})
        self.assertEqual(SUPPORT.cue_times([{"id": "prompt", "seconds": 1}], 3, 30, None)["prompt"]["frame"], 30)

    def test_invalid_or_unrenderable_cues_fail(self):
        timing = SUPPORT.timing_config({"bpm": 120})
        cases = [
            ("oops", timing), ([True], timing),
            ([{"id": "same", "seconds": 0}, {"id": "same", "beat": 1}], timing),
            ([{"id": "a.b", "seconds": 0}], timing),
            ([{"id": "prompt", "seconds": 1, "beat": 2}], timing),
            ([{"id": "prompt"}], timing),
            ([{"id": "prompt", "seconds": -1}], timing),
            ([{"id": "prompt", "seconds": True}], timing),
            ([{"id": "prompt", "seconds": float("nan")}], timing),
            ([{"id": "prompt", "seconds": 2}], timing),
            # A valid timestamp can still round to the first frame beyond
            # the scene; reject it rather than silently hiding the cue.
            ([{"id": "prompt", "seconds": 1.999}], timing),
            ([{"id": "prompt", "beat": 4}], timing),
            ([{"id": "prompt", "beat": -1}], timing),
            ([{"id": "prompt", "beat": 1}], None),
            ([{"id": "prompt", "seconds": 1, "typo": 3}], timing),
        ]
        for cues, config in cases:
            with self.subTest(cues=cues), self.assertRaises(ValueError):
                SUPPORT.cue_times(cues, 2, 30, config)


if __name__ == "__main__":
    unittest.main()
