"""Review-evidence planning, motion advisory, and ffmpeg sheet generation.

Run with: python3 -m unittest discover -s skills/mandarinai-video/tests -v
The sheet test needs ffmpeg/ffprobe on PATH and is skipped otherwise.
"""

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


SKILL = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("review_evidence", SKILL / "scripts" / "review_evidence.py")
REVIEW = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REVIEW)
HAS_FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def scene(start, duration, **extra):
    return {"start": start, "duration": duration, "frames": round(duration * 10), "hold": 1, **extra}


class FramePlanTests(unittest.TestCase):
    def test_scan_samples_three_frames_per_second_from_the_first_frame(self):
        self.assertEqual(REVIEW.scan_frames(total_frames=31, fps=30), [0, 10, 20, 30])

    def test_scan_never_steps_by_zero_at_low_frame_rates(self):
        self.assertEqual(REVIEW.scan_frames(total_frames=3, fps=2), [0, 1, 2])

    def test_cue_frames_are_absolute_and_bracket_the_reveal(self):
        manifest = {"scenes": [scene(0, 2), scene(2, 2, heading="比", cues={"content": {"seconds": 0.5, "frame": 5}})]}
        [cue] = REVIEW.cue_frames(manifest, fps=10, total_frames=40)
        self.assertEqual((cue["scene"], cue["cue"], cue["heading"]), (2, "content", "比"))
        self.assertAlmostEqual(cue["seconds"], 2.5)
        self.assertEqual((cue["before_frame"], cue["after_frame"]), (24, 29))

    def test_cue_frames_clamp_to_the_video(self):
        manifest = {"scenes": [scene(0, 1, cues={"start": {"seconds": 0, "frame": 0}, "end": {"seconds": 0.9, "frame": 9}})]}
        frames = {c["cue"]: (c["before_frame"], c["after_frame"]) for c in REVIEW.cue_frames(manifest, fps=10, total_frames=10)}
        self.assertEqual(frames, {"start": (0, 4), "end": (8, 9)})

    def test_projects_without_cues_have_no_cue_frames(self):
        self.assertEqual(REVIEW.cue_frames({"scenes": [scene(0, 2)]}, fps=10, total_frames=20), [])


class HoldWindowTests(unittest.TestCase):
    def test_voiced_scene_holds_from_the_end_of_its_last_track(self):
        tracks = [{"start": 0.5, "duration": 1.0}, {"start": 1.85, "duration": 0.9}]
        self.assertEqual(REVIEW.hold_windows({"scenes": [scene(4, 5, voice_tracks=tracks)]}), [(6.75, 9)])

    def test_legacy_single_audio_uses_offset_and_measured_duration(self):
        item = scene(0, 4, audio="a.mp3", audio_offset=0.5, audio_duration=2.0)
        self.assertEqual(REVIEW.hold_windows({"scenes": [item]}), [(2.5, 4)])

    def test_silent_dialogue_uses_estimated_line_timing(self):
        lines = [{"start": 0.35, "duration": 1.2}]
        self.assertEqual(REVIEW.hold_windows({"scenes": [scene(0, 3, lines=lines)]}), [(1.55, 3)])

    def test_unvoiced_scene_holds_for_its_declared_hold(self):
        self.assertEqual(REVIEW.hold_windows({"scenes": [scene(2, 3, hold=2)]}), [(3, 5)])


def frames_for(values, size=16):
    return [bytes([v]) * size for v in values]


class MotionAdvisoryTests(unittest.TestCase):
    def changing_then_still(self, still_seconds, interval=0.1):
        moving = [(i * 37) % 200 for i in range(round(3 / interval))]
        still = [moving[-1]] * round(still_seconds / interval)
        return frames_for(moving + still), interval, 3 + still_seconds

    def test_static_stretch_outside_holds_is_flagged(self):
        samples, interval, duration = self.changing_then_still(4)
        summary = REVIEW.motion_summary(samples, interval, duration, holds=[])
        self.assertEqual(summary["status"], "advisory")
        [run] = summary["static_runs"]
        self.assertAlmostEqual(run["start"], 2.9, places=6)
        self.assertAlmostEqual(run["seconds"], 4.0, places=6)
        self.assertTrue(run["flagged"])
        self.assertIn("static", " ".join(summary["notes"]))

    def test_the_same_stretch_inside_a_hold_is_expected(self):
        samples, interval, duration = self.changing_then_still(4)
        summary = REVIEW.motion_summary(samples, interval, duration, holds=[(2.8, 7)])
        self.assertFalse(summary["static_runs"][0]["flagged"])
        self.assertEqual(summary["flat_cell_pairs"], [])
        self.assertEqual(summary["notes"], [])

    def test_flat_cell_pairs_outside_holds_are_listed(self):
        samples, interval, duration = self.changing_then_still(5)
        summary = REVIEW.motion_summary(samples, interval, duration, holds=[])
        self.assertEqual([(pair["from"], pair["to"]) for pair in summary["flat_cell_pairs"]], [(5.0, 7.5)])
        self.assertGreater(summary["average_cell_change"], 0)

    def test_moving_share_counts_sampled_pairs(self):
        summary = REVIEW.motion_summary(frames_for([0, 50, 50, 100, 100]), 0.1, 0.5, holds=[])
        self.assertAlmostEqual(summary["moving_share"], 0.5)

    def test_frame_difference_is_mean_absolute_difference(self):
        self.assertAlmostEqual(REVIEW.mean_difference(bytes([0, 10, 20, 30]), bytes([5, 10, 10, 30])), 3.75)


@unittest.skipUnless(HAS_FFMPEG, "ffmpeg/ffprobe not installed")
class SheetTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="mandarinai-review-test-")
        self.addCleanup(temporary.cleanup)
        self.work = Path(temporary.name)
        self.video = self.work / "clip.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=320x180:rate=10:duration=12",
                        "-pix_fmt", "yuv420p", str(self.video)], check=True)

    def size(self, path):
        stream = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(path)],
                                           capture_output=True, text=True, check=True).stdout)["streams"][0]
        return stream["width"], stream["height"]

    def test_review_writes_scan_cue_and_phone_sheets_with_an_index(self):
        manifest = {"scenes": [scene(0, 6, cues={"content": {"seconds": 1, "frame": 10}}), scene(6, 6)]}
        stills = []
        for name, time in (("first-content", 1), ("ending", 11)):
            path = self.work / f"{name}.png"
            subprocess.run(["ffmpeg", "-v", "error", "-ss", str(time), "-i", str(self.video), "-frames:v", "1", str(path)], check=True)
            stills.append(path)
        out = self.work / "qa"
        out.mkdir()
        report = REVIEW.write_review(self.video, manifest, fps=10, width=320, height=180, total_frames=120,
                                     out_dir=out, stills=stills)
        # 120 frames sampled every 3rd frame is 40 cells: one full 4x8 sheet and one partial sheet.
        self.assertEqual([sheet["file"] for sheet in report["scan_sheets"]], ["scan-01.png", "scan-02.png"])
        self.assertEqual(report["scan_sheets"][0]["cells"], 32)
        self.assertAlmostEqual(report["scan_sheets"][1]["first_seconds"], 32 * 3 / 10)
        self.assertEqual(self.size(out / "scan-01.png"), REVIEW.sheet_size(4, 8, 480, 270))
        self.assertEqual(report["cue_sheets"][0]["file"], "cues-01.png")
        self.assertEqual(report["cue_sheets"][0]["cues"][0]["cue"], "content")
        self.assertEqual(self.size(out / "cues-01.png"), REVIEW.sheet_size(4, 1, 480, 270))
        self.assertEqual(report["phone_sheet"], "phone-width.png")
        self.assertEqual(self.size(out / "phone-width.png"), REVIEW.sheet_size(1, 2, 480, 270))
        self.assertEqual(report["motion"]["status"], "advisory")
        index = (out / "review.txt").read_text(encoding="utf-8")
        self.assertIn("scan-02.png", index)
        self.assertIn("content", index)

    def test_portrait_cells_keep_a_480_pixel_long_side(self):
        self.assertEqual(REVIEW.cell_size(1080, 1920), (270, 480))
        self.assertEqual(REVIEW.cell_size(1920, 1080), (480, 270))
        self.assertEqual(REVIEW.scan_columns(1080, 1920), 8)
        self.assertEqual(REVIEW.scan_columns(1920, 1080), 4)


if __name__ == "__main__":
    unittest.main()
