"""Manifest validation and real audio mixing for cast narration.

Run: python3 -m unittest discover -s skills/mandarinai-video/tests -v
"""
import array
import copy
import math
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

SKILL = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("render_voice_tracks", SKILL / "scripts/render-project.py")
RENDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RENDER)
HAS_AUDIO_TOOLS = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


class VoiceManifestTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="mandarinai-cast-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.project = self.root / "project"
        (self.project / "assets").mkdir(parents=True)
        (self.project / "scene.html").write_text("<p>Cast lesson</p>")
        for file in ("one.wav", "two.wav", "music.wav", "jin.webp", "yue.webp"):
            (self.project / "assets" / file).write_bytes(b"local fixture")
        self.manifest = {
            "schema_version": 1, "dimensions": {"width": 320, "height": 568},
            "fps": 10, "frames": 40, "duration": 4, "audio_mode": "narrated", "bgm": None,
            "cast": {"presenter": "jin", "characters": {
                "jin": {"id": "jin", "name": "Jin", "portrait": "assets/jin.webp"},
                "yue": {"id": "yue", "name": "Yue", "portrait": "assets/yue.webp"},
            }},
            "scenes": [{"file": "scene.html", "frames": 40, "duration": 4, "start": 0,
                        "speaker": "jin", "audio": "missing-legacy.wav", "voice_tracks": [
                            {"file": "assets/one.wav", "speaker": "jin", "voice": None,
                             "source": "local", "start": 0.5, "duration": 0.5},
                            {"file": "assets/two.wav", "speaker": "yue", "voice": "zh-CN-XiaoyiNeural",
                             "source": "tts", "start": 1.5, "duration": 0.5},
                        ]}],
        }

    def validate(self, manifest=None, actual=0.5):
        manifest = copy.deepcopy(self.manifest if manifest is None else manifest)
        with mock.patch.object(RENDER, "measured_audio", return_value=actual):
            result = RENDER.validate(self.project, manifest)
        return manifest, result

    def test_named_tracks_are_measured_and_supersede_legacy_audio(self):
        manifest, result = self.validate()
        self.assertEqual(result, (320, 568, 10, 40, True))
        tracks = list(RENDER.voice_tracks(manifest))
        self.assertEqual(len(tracks), 2)
        self.assertIsNone(manifest["scenes"][0]["audio_path"])
        self.assertEqual(tracks[0][1]["path"], self.project / "assets/one.wav")
        self.assertIsNone(tracks[0][1]["voice"])
        self.assertEqual(tracks[1][1]["actual_duration"], 0.5)

    def test_explicit_empty_tracks_are_authoritative_for_silent_drafts(self):
        self.manifest["scenes"][0]["voice_tracks"] = []
        self.manifest["audio_mode"] = "silent"
        self.assertEqual(self.validate()[1][-1], False)

    def test_legacy_single_audio_remains_valid_without_a_cast(self):
        del self.manifest["cast"]
        scene = self.manifest["scenes"][0]
        del scene["voice_tracks"]
        del scene["speaker"]
        scene.update(audio="assets/one.wav", audio_offset=0.5, audio_duration=0.5)
        manifest, _ = self.validate()
        self.assertEqual(list(RENDER.voice_tracks(manifest))[0][1]["start"], 0.5)

    def test_changed_recording_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "duration changed"):
            self.validate(actual=0.9)

    def test_overlapping_and_out_of_bounds_tracks_are_rejected(self):
        for start in (0.7, 3.8):
            with self.subTest(start=start):
                manifest = copy.deepcopy(self.manifest)
                manifest["scenes"][0]["voice_tracks"][1]["start"] = start
                with self.assertRaises(ValueError):
                    self.validate(manifest)

    def test_track_offsets_and_durations_must_be_finite(self):
        for field, value in (("start", float("nan")), ("duration", float("inf")),
                             ("duration", 0), ("start", -0.1), ("duration", True)):
            with self.subTest(field=field, value=value):
                manifest = copy.deepcopy(self.manifest)
                manifest["scenes"][0]["voice_tracks"][0][field] = value
                with self.assertRaises(ValueError):
                    self.validate(manifest)

    def test_missing_unknown_or_escaping_track_media_is_rejected(self):
        outside = self.root / "outside.wav"
        outside.write_bytes(b"outside fixture")
        (self.project / "assets/linked.wav").symlink_to(outside)
        for relative in ("assets/missing.wav", "../outside.wav", str(outside), "assets/linked.wav"):
            with self.subTest(relative=relative):
                manifest = copy.deepcopy(self.manifest)
                manifest["scenes"][0]["voice_tracks"][0]["file"] = relative
                with self.assertRaises(ValueError):
                    self.validate(manifest)

    def test_unknown_speaker_and_escaping_portrait_are_rejected(self):
        for place in ("scene", "track", "presenter", "portrait"):
            with self.subTest(place=place):
                manifest = copy.deepcopy(self.manifest)
                if place == "scene":
                    manifest["scenes"][0]["speaker"] = "unknown"
                elif place == "track":
                    manifest["scenes"][0]["voice_tracks"][0]["speaker"] = "unknown"
                elif place == "presenter":
                    manifest["cast"]["presenter"] = "unknown"
                else:
                    manifest["cast"]["characters"]["jin"]["portrait"] = "../outside.webp"
                with self.assertRaises(ValueError):
                    self.validate(manifest)

    def test_audio_mode_and_expected_audio_must_match_tracks(self):
        for mode in ("silent", "music"):
            with self.subTest(mode=mode):
                manifest = copy.deepcopy(self.manifest)
                manifest["audio_mode"] = mode
                with self.assertRaises(ValueError):
                    self.validate(manifest)
        manifest = copy.deepcopy(self.manifest)
        manifest["expected_audio"] = False
        with self.assertRaisesRegex(ValueError, "expected_audio"):
            self.validate(manifest)
        manifest["scenes"][0]["voice_tracks"] = []
        with self.assertRaisesRegex(ValueError, "audio_mode"):
            self.validate(manifest)

    def test_music_ducking_defaults_on_and_can_be_disabled(self):
        self.manifest["bgm"] = {"file": "assets/music.wav", "volume": 0.12}
        for duck in (None, True, False):
            with self.subTest(duck=duck):
                if duck is not None:
                    self.manifest["bgm"]["duck"] = duck
                manifest, _ = self.validate()
                command = RENDER.audio_mix_command("joined.mp4", "final.mp4", manifest, 4)
                filters = command[command.index("-filter_complex") + 1]
                self.assertEqual("sidechaincompress" in filters, duck is not False)
                self.assertIn("adelay=500:all=1", filters)
                self.assertIn("adelay=1500:all=1", filters)
                self.assertIn("apad,asetpts=N/SR/TB,atrim=duration=4", filters)
                self.assertNotIn("-shortest", command)
                self.assertEqual(command.count(str(self.project / "assets/one.wav")), 1)

    def test_music_without_narration_does_not_need_a_sidechain(self):
        self.manifest["bgm"] = {"file": "assets/music.wav", "volume": 0.12}
        self.manifest["audio_mode"] = "music"
        self.manifest["scenes"][0]["voice_tracks"] = []
        manifest, _ = self.validate()
        command = RENDER.audio_mix_command("joined.mp4", "final.mp4", manifest, 4)
        self.assertNotIn("sidechaincompress", command[command.index("-filter_complex") + 1])


@unittest.skipUnless(HAS_AUDIO_TOOLS, "ffmpeg and ffprobe are required")
class ActualMixTests(unittest.TestCase):
    setUp = VoiceManifestTests.setUp

    def ffmpeg(self, args):
        result = subprocess.run(["ffmpeg", "-n", "-v", "error", *args], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)

    def mix_fixture(self, *, music=True):
        for name, hz in (("one", 880), ("two", 1320), ("music", 220)):
            audio = self.project / "assets" / f"{name}.wav"
            audio.unlink()
            self.ffmpeg(["-f", "lavfi", "-i", f"sine=frequency={hz}:sample_rate=48000:duration=0.5", str(audio)])
        joined = self.root / "joined.mp4"
        completed = self.root / "completed.mp4"
        self.ffmpeg(["-f", "lavfi", "-i", "color=c=navy:s=32x32:r=10:d=4", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(joined)])
        if music:
            self.manifest["bgm"] = {"file": "assets/music.wav", "volume": 0.12}
        manifest = copy.deepcopy(self.manifest)
        RENDER.validate(self.project, manifest)
        result = subprocess.run(RENDER.audio_mix_command(joined, completed, manifest, 4), capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        return completed

    def levels(self, completed):
        result = subprocess.run(["ffmpeg", "-v", "error", "-i", str(completed), "-ac", "1",
                                 "-ar", "48000", "-f", "f32le", "pipe:1"], capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        samples = array.array("f", result.stdout)
        def rms(start, end):
            part = samples[round(start * 48000):round(end * 48000)]
            return math.sqrt(sum(sample * sample for sample in part) / len(part))
        return rms

    def test_two_speakers_with_looped_ducked_music_cover_the_closing_hold(self):
        completed = self.mix_fixture()
        evidence = RENDER.probe(completed)
        audio = next(stream for stream in evidence["streams"] if stream["codec_type"] == "audio")
        self.assertEqual(audio["codec_name"], "aac")
        self.assertAlmostEqual(float(audio["duration"]), 4, delta=0.02)
        self.assertAlmostEqual(float(evidence["format"]["duration"]), 4, delta=0.02)
        rms = self.levels(completed)
        # A full-length AAC stream can contain only quiet music. Require both
        # utterances to be audible at their declared starts above the music bed.
        music_level = rms(2.5, 2.8)
        for start, end in ((0.6, 0.9), (1.6, 1.9)):
            self.assertGreater(rms(start, end), max(0.03, music_level * 4))
        self.assertGreater(music_level, 0.001)

    def test_voice_only_mix_has_speech_at_both_offsets_and_silence_between(self):
        completed = self.mix_fixture(music=False)
        rms = self.levels(completed)
        self.assertLess(rms(0.05, 0.35), 0.0001)
        self.assertGreater(rms(0.6, 0.9), 0.03)
        self.assertLess(rms(1.1, 1.4), 0.0001)
        self.assertGreater(rms(1.6, 1.9), 0.03)
        self.assertLess(rms(2.2, 3.5), 0.0001)


if __name__ == "__main__":
    unittest.main()
