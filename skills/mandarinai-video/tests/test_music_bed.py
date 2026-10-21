"""Offline checks for the original, declared-tempo music bed generator."""

from array import array
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import wave


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "make-music-bed.py"
SPEC = importlib.util.spec_from_file_location("make_music_bed", SCRIPT)
MUSIC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MUSIC)


class MusicBedTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="mandarinai-music-test-")
        self.addCleanup(temporary.cleanup)
        self.work = Path(temporary.name)

    def generate(self, name="music.wav", **options):
        output = self.work / name
        defaults = {"bpm": 120, "bars": 2, "sample_rate": 8000, "out": output}
        MUSIC.make_music(**(defaults | options))
        with wave.open(str(output), "rb") as audio:
            params = audio.getparams()
            samples = array("h", audio.readframes(audio.getnframes()))
        if sys.byteorder != "little":
            samples.byteswap()
        return output, params, samples

    def test_cli_produces_pcm_stereo_and_truthful_metadata(self):
        output = self.work / "three-beats.wav"
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--bpm", "120", "--bars", "2", "--beats-per-bar", "3",
             "--sample-rate", "8000", "--out", str(output)], capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        with wave.open(str(output), "rb") as audio:
            self.assertEqual((audio.getnchannels(), audio.getsampwidth(), audio.getframerate()), (2, 2, 8000))
            self.assertEqual(audio.getnframes(), 24000)
            self.assertEqual(audio.getcomptype(), "NONE")
        metadata = json.loads(output.with_suffix(".music.json").read_text())
        self.assertEqual(metadata["duration"], 3)
        self.assertEqual(metadata["sample_count"], 24000)
        self.assertEqual((metadata["bpm"], metadata["bars"], metadata["beats_per_bar"]), (120, 2, 3))
        self.assertTrue(metadata["original_synthesized"])
        self.assertFalse(metadata["sampled_assets"])
        self.assertEqual(metadata["recipe"], "mandarinai-warm-sevenths-v1")
        self.assertIn("no beat detection or time-stretch", metadata["timing_note"])

    def test_identical_parameters_produce_identical_wav_bytes(self):
        first, _, _ = self.generate("first.wav", bpm=97, bars=1)
        second, _, _ = self.generate("second.wav", bpm=97, bars=1)
        self.assertEqual(first.read_bytes(), second.read_bytes())
        self.assertEqual(first.with_suffix(".music.json").read_bytes(), second.with_suffix(".music.json").read_bytes())

    def test_tempo_controls_exact_sample_count_without_accumulated_rounding(self):
        _, slow, _ = self.generate("slow.wav", bpm=97, bars=3, beats_per_bar=5)
        _, fast, _ = self.generate("fast.wav", bpm=194, bars=3, beats_per_bar=5)
        self.assertEqual(slow.nframes, round(3 * 5 * 60 / 97 * 8000))
        self.assertEqual(fast.nframes, round(3 * 5 * 60 / 194 * 8000))
        self.assertLessEqual(abs(slow.nframes - 2 * fast.nframes), 1)

    def test_audible_unclipped_stereo_with_faded_edges(self):
        _, _, samples = self.generate(gain=1)
        self.assertGreater(max(map(abs, samples)), 3000)
        self.assertLess(max(map(abs, samples)), 32767)
        self.assertEqual(list(samples[:2]), [0, 0])
        self.assertEqual(list(samples[-2:]), [0, 0])
        self.assertNotEqual(samples[::2], samples[1::2])

    def test_repeated_note_energy_rises_on_the_declared_beat_grid(self):
        _, params, samples = self.generate()
        mono = samples[::2]

        def rms(start, end):
            window = mono[round(start * params.framerate):round(end * params.framerate)]
            return math.sqrt(sum(value * value for value in window) / len(window))

        # At 120 BPM the musical attacks recur every half second. A preceding
        # quiet interval and a clear attack distinguish a pulse from a static tone.
        for beat in range(1, 8):
            onset = beat * 0.5
            with self.subTest(beat=beat):
                before = rms(onset - 0.09, onset - 0.025)
                attack = rms(onset + 0.025, onset + 0.1)
                self.assertGreater(attack, 100)
                self.assertGreater(attack, before * 5)

    def test_refuses_existing_wav_or_metadata_without_altering_either(self):
        for collision in ("music.wav", "music.music.json"):
            with self.subTest(collision=collision):
                output = self.work / "music.wav"
                metadata = output.with_suffix(".music.json")
                existing = self.work / collision
                existing.write_bytes(b"preserve me")
                with self.assertRaisesRegex(ValueError, "already exists"):
                    MUSIC.make_music(bpm=120, bars=1, out=output)
                self.assertEqual(existing.read_bytes(), b"preserve me")
                self.assertFalse((metadata if existing == output else output).exists())
                existing.unlink()

    def test_refuses_dangling_symlink_outputs(self):
        output = self.work / "music.wav"
        output.symlink_to(self.work / "missing.wav")
        with self.assertRaisesRegex(ValueError, "already exists"):
            MUSIC.make_music(bpm=120, bars=1, out=output)
        self.assertTrue(output.is_symlink())
        self.assertFalse((self.work / "missing.wav").exists())

    def test_invalid_cli_values_fail_before_creating_files(self):
        bad_options = [
            ("--bpm", "nan"), ("--bpm", "inf"), ("--bpm", "19"), ("--bpm", "241"),
            ("--bars", "0"), ("--bars", "129"), ("--bars", "1.5"),
            ("--beats-per-bar", "0"), ("--beats-per-bar", "13"),
            ("--sample-rate", "7999"), ("--sample-rate", "96001"),
            ("--gain", "0"), ("--gain", "1.01"), ("--gain", "nan"),
        ]
        output = self.work / "invalid.wav"
        for option, value in bad_options:
            with self.subTest(option=option, value=value):
                result = subprocess.run(
                    [sys.executable, str(SCRIPT), "--bpm", "120", "--bars", "1",
                     "--out", str(output), option, value], capture_output=True, text=True,
                )
                self.assertEqual(result.returncode, 2)
                self.assertIn("error:", result.stderr)
                self.assertFalse(output.exists())
                self.assertFalse(output.with_suffix(".music.json").exists())

    def test_duration_cap_output_extension_and_api_integer_validation(self):
        with self.assertRaisesRegex(ValueError, "10 minutes"):
            MUSIC.make_music(bpm=20, bars=128, beats_per_bar=12, out=self.work / "long.wav")
        with self.assertRaisesRegex(ValueError, "end in .wav"):
            MUSIC.make_music(bpm=120, bars=1, out=self.work / "wrong.mp3")
        for options in ({"bars": True}, {"beats_per_bar": 4.0}, {"sample_rate": False}):
            with self.subTest(options=options), self.assertRaisesRegex(ValueError, "integer"):
                MUSIC.make_music(**({"bpm": 120, "bars": 1, "out": self.work / "invalid.wav"} | options))
        self.assertEqual(list(self.work.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
