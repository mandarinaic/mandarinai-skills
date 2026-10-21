"""Offline regression coverage for source bundles and editable video projects.

Run with: python3 -m unittest discover -s skills/mandarinai-video/tests -v
No API, TTS service, browser, or installed Node packages are required.
"""

import argparse
import contextlib
import copy
from html.parser import HTMLParser
import importlib.util
import io
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from urllib.parse import parse_qs, urlsplit


SKILL = Path(__file__).resolve().parents[1]
FIXTURES = SKILL / "examples" / "sources"


def script_module(name):
    spec = importlib.util.spec_from_file_location(
        name.replace("-", "_"), SKILL / "scripts" / f"{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PREPARE = script_module("prepare-content")
BUILD = script_module("build-project")
RENDER = script_module("render-project")
HAS_AUDIO_TOOLS = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


class Elements(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.elements = []
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


class OfflineCase(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="mandarinai-video-test-")
        self.addCleanup(temporary.cleanup)
        self.work = Path(temporary.name).resolve()
        self.serial = 0

    def path(self, suffix):
        self.serial += 1
        return self.work / f"{self.serial}-{suffix}"

    def read_json(self, path):
        return json.loads(path.read_text(encoding="utf-8"))

    def write_json(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return path

    def fixture(self, kind):
        return self.read_json(FIXTURES / f"{kind}.json")

    def prepare(self, kind="word", payload=None, language="en", out=None):
        payload = self.fixture(kind) if payload is None else payload
        record = payload["data"] if "code" in payload else payload
        source_input = self.write_json(self.path("detail.json"), payload)
        out = out or self.path("source.json")
        args = argparse.Namespace(
            kind=kind,
            id=str(record["id"]),
            language=language,
            input=str(source_input),
            api_base=None,
            site_base="https://learn.example",
            out=str(out),
        )
        with mock.patch.object(PREPARE, "fetch", side_effect=AssertionError("unexpected network request")):
            with contextlib.redirect_stdout(io.StringIO()):
                PREPARE.prepare(args)
        return out, self.read_json(out)

    def brief(self, source, scenes=None, **fields):
        return {
            "source": str(source),
            "mode": "tutorial",
            "fps": 24,
            "scenes": scenes if scenes is not None else [
                {"layout": "lesson", "heading": "Learn a word", "text": "学习", "duration": 1.01}
            ],
            **fields,
        }

    def build(self, brief, *, silent=False, out=None, source=None):
        brief_path = self.write_json(self.path("brief.json"), brief)
        out = out or self.path("project")
        args = argparse.Namespace(
            brief=str(brief_path), out=str(out), source=str(source) if source else None,
            tts=False, silent=silent, voice="unused", tts_url="https://example.invalid/tts",
        )
        with mock.patch.object(BUILD, "fetch_tts", side_effect=AssertionError("unexpected TTS request")):
            with contextlib.redirect_stdout(io.StringIO()):
                BUILD.build(args)
        return out, self.read_json(out / "project.json")

    def validate(self, project, manifest):
        # Validation adds resolved Path values; callers retain a reusable JSON manifest.
        return RENDER.validate(project, copy.deepcopy(manifest))

    def wave(self, path, seconds):
        result = subprocess.run(
            ["ffmpeg", "-n", "-v", "error", "-f", "lavfi", "-i",
             f"sine=frequency=440:sample_rate=48000:duration={seconds}",
             "-c:a", "pcm_s16le", str(path)],
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
            capture_output=True, text=True, check=True, timeout=30,
        )
        return float(json.loads(probe.stdout)["format"]["duration"])


class SourceTests(OfflineCase):
    def test_all_fixture_shapes_survive_normalization(self):
        for kind in ("word", "grammar", "university", "article"):
            with self.subTest(kind=kind):
                fixture = self.fixture(kind)
                record = fixture["data"]
                _, bundle = self.prepare(kind)
                self.assertEqual(bundle["id"], str(record["id"]))
                self.assertEqual(bundle["kind"], kind)
                self.assertEqual(bundle["raw"], record)
                self.assertTrue(bundle["provenance"]["synthetic"])
                content = bundle["content"]
                if kind == "word":
                    self.assertEqual(content["meanings"], record["meanings"])
                    self.assertIsInstance(content["examples"][0]["translations"], dict)
                    self.assertEqual(content["examples"], record["structured_examples"])
                elif kind == "grammar":
                    self.assertEqual(content["content_groups"], record["content_groups"])
                    sentence = content["content_groups"][0]["sentences"][0]
                    self.assertIsInstance(sentence["translations"], list)
                    self.assertEqual(sentence["translations"][0]["language"], "en")
                elif kind == "university":
                    expected = list(dict.fromkeys(record["images"] + [
                        image for campus in record["campuses"] for image in campus["images"]
                    ]))
                    self.assertEqual(content["gallery"], expected)
                    self.assertGreater(len(expected), len(record["images"]))
                else:
                    self.assertEqual(content["sentences"], record["sentences"])
                    self.assertEqual(content["content_blocks"], record["content_blocks"])
                    sentence_indices = [block["sentence_index"] for block in content["content_blocks"]
                                        if block["type"] == "sentence"]
                    self.assertEqual(sentence_indices, list(range(len(content["sentences"]))))
                    self.assertEqual([s["sentence_order"] for s in content["sentences"]], [1, 2])
                    segment = content["sentences"][0]["word_segments"][0]
                    self.assertIsInstance(segment["word_info"]["translations"], list)

    def test_word_prefers_structured_examples_without_discarding_raw_legacy(self):
        payload = self.fixture("word")
        payload["data"]["examples"] = ["Legacy example"]
        payload["data"]["hsk_level"] = 7
        _, bundle = self.prepare(payload=payload)
        self.assertEqual(bundle["content"]["examples"], payload["data"]["structured_examples"])
        self.assertEqual(bundle["raw"]["examples"], ["Legacy example"])
        self.assertEqual(bundle["content"]["hsk_level_label"], "7–9")

    def test_translation_maps_and_arrays_are_not_interchangeable(self):
        cases = []
        word = self.fixture("word")
        word["data"]["structured_examples"][0]["translations"] = [{"language": "en", "translation": "study"}]
        cases.append(("word", word))
        grammar = self.fixture("grammar")
        grammar["data"]["content_groups"][0]["sentences"][0]["translations"] = {"en": "hotter"}
        cases.append(("grammar", grammar))
        article = self.fixture("article")
        article["data"]["sentences"][0]["word_segments"][0]["word_info"]["translations"] = {"en": "I"}
        cases.append(("article", article))
        university = self.fixture("university")
        university["data"]["campuses"][0]["images"] = {"image": "campus.jpg"}
        cases.append(("university", university))
        for kind, payload in cases:
            with self.subTest(kind=kind):
                output = self.path("rejected.json")
                with self.assertRaises(ValueError):
                    self.prepare(kind, payload, out=output)
                self.assertFalse(output.exists())

    def test_locale_urls_and_synthetic_library_links(self):
        routes = {
            "word": "/hsk/word/list/1", "grammar": "/grammar/list/1",
            "university": "/university/list/1", "article": "/tools/articles",
        }
        for kind, route in routes.items():
            for locale, prefix in (("en", ""), ("zh", "/zh"), ("es", "/es"), ("ja", "")):
                with self.subTest(kind=kind, locale=locale):
                    _, bundle = self.prepare(kind, language=locale)
                    self.assertEqual(bundle["url"], "https://learn.example" + prefix + route)
                    self.assertEqual(bundle["language"], locale)

    def test_large_integer_id_stays_exact_in_json_detail_and_api_urls(self):
        payload = self.fixture("word")
        exact_id = 9223372036854775807
        payload["data"]["id"] = exact_id
        del payload["data"]["_fixture"]
        output, bundle = self.prepare(payload=payload, language="fr")
        self.assertEqual(bundle["id"], str(exact_id))
        self.assertEqual(bundle["raw"]["id"], exact_id)
        self.assertEqual(bundle["url"], f"https://learn.example/fr/hsk/word/detail/{exact_id}")
        self.assertIn(str(exact_id), output.read_text(encoding="utf-8"))
        api = PREPARE.api_url("word", bundle["id"], "fr", "https://api.example")
        self.assertEqual(parse_qs(urlsplit(api).query)["id"], [str(exact_id)])
        with self.assertRaises(ValueError):
            PREPARE.content_id(float(exact_id))

    def test_unsuccessful_or_ambiguous_envelopes_are_rejected(self):
        record = self.fixture("word")["data"]
        requested_id = str(record["id"])
        failures = [
            {"code": 500, "data": record}, {"code": "200", "data": record},
            {"code": True, "data": record}, {"code": 200}, {"data": record},
            {"code": 200, "data": [record]}, {"code": 200, "id": record["id"], "data": record},
            {"code": 200, "data": {"result": record}},
            {**record, "id": requested_id + "-different"},
        ]
        for payload in failures:
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    PREPARE.detail_record(payload, requested_id)
        self.assertEqual(PREPARE.detail_record(record, requested_id), record)
        self.assertEqual(PREPARE.detail_record({"code": 200, "data": record}, requested_id), record)
        with self.assertRaises(ValueError):
            PREPARE.parse_json('{"code": 200, "code": 500, "data": {}}')

    def test_source_output_is_never_replaced(self):
        output = self.path("existing-source.json")
        sentinel = b'{"preserve": "reviewed source"}\n'
        output.write_bytes(sentinel)
        with self.assertRaises(ValueError):
            self.prepare(out=output)
        self.assertEqual(output.read_bytes(), sentinel)


class BuildTests(OfflineCase):
    def test_source_override_resolves_relative_to_current_directory(self):
        source_path, source = self.prepare()
        brief_path = self.write_json(self.work / "nested" / "brief.json", self.brief("missing-source.json"))
        project = self.path("project")
        result = subprocess.run(
            [sys.executable, str(SKILL / "scripts" / "build-project.py"), str(brief_path),
             "--source", source_path.name, "--out", str(project)],
            cwd=self.work, capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.read_json(project / "source.json"), source)
        self.assertEqual(self.read_json(project / "project.json")["source"], source)

    def test_narration_requires_audio_or_explicit_silent_draft(self):
        source_path, _ = self.prepare()
        narration = "我每天学习中文。"
        brief = self.brief(source_path, [{"layout": "lesson", "heading": "Practice", "narration": narration}])
        output = self.path("project")
        with self.assertRaises(ValueError):
            self.build(brief, out=output)
        self.assertFalse(output.exists())
        project, manifest = self.build(brief, silent=True, out=output)
        self.assertEqual(manifest["audio_mode"], "silent")
        self.assertTrue(manifest["pending_narration"])
        self.assertTrue(manifest["scenes"][0]["pending_narration"])
        self.assertIsNone(manifest["scenes"][0]["audio"])
        self.assertIn(narration, (project / "captions.srt").read_text(encoding="utf-8"))
        script = (project / "script.md").read_text(encoding="utf-8")
        self.assertIn(narration, script)
        self.assertTrue(any(line.startswith("Audio:") and "PENDING" in line for line in script.splitlines()))
        self.assertFalse(any("audio" in path.name for path in (project / "assets").iterdir()))

    def test_valid_pinyin_aligns_only_hanzi_and_escapes_markup(self):
        expected = "<ruby>你<rt>nǐ</rt></ruby><ruby>好<rt>hǎo</rt></ruby>，A &amp; B！"
        for pinyin in ("nǐ hǎo", ["nǐ", "hǎo"]):
            with self.subTest(pinyin=pinyin):
                self.assertEqual(BUILD.ruby_text("你好，A & B！", pinyin), expected)
        self.assertEqual(BUILD.ruby_text("<b>&", None), "&lt;b&gt;&amp;")
        self.assertEqual(BUILD.ruby_text("你好", ["NI\u030c", "HA\u030cO"]),
                         "<ruby>你<rt>nǐ</rt></ruby><ruby>好<rt>hǎo</rt></ruby>")

    def test_invalid_pinyin_fails_before_creating_project(self):
        source_path, _ = self.prepare()
        for pinyin in ("nǐ", "nǐ hǎo ma", ["nǐ hǎo", "ma"], ["nǐ", 3],
                       {"你": "nǐ"}, ["ni3", "hao3"], ["<script>", "hǎo"], ["nǐ", "好"]):
            with self.subTest(pinyin=pinyin):
                output = self.path("invalid-pinyin")
                scene = {"layout": "lesson", "heading": "Pronunciation", "text": "你好。", "pinyin": pinyin}
                with self.assertRaises(ValueError):
                    self.build(self.brief(source_path, [scene]), out=output)
                self.assertFalse(output.exists())

    def test_scene_and_preview_escape_editorial_html_without_losing_text(self):
        source_path, _ = self.prepare()
        markup = '</script><img src=x onerror=alert(1)> & "quoted"'
        scene = {"layout": "lesson", "heading": markup, "text": "你好，" + markup,
                 "pinyin": ["nǐ", "hǎo"], "translation": markup,
                 "label": markup, "bullets": [markup]}
        project, manifest = self.build(self.brief(source_path, [scene], title=markup))
        scene_html = (project / manifest["scenes"][0]["file"]).read_text(encoding="utf-8")
        self.assertIn("&lt;img src=x onerror=alert(1)&gt;", scene_html)
        self.assertIn("<rt>nǐ</rt>", scene_html)
        for page in (scene_html, (project / "preview.html").read_text(encoding="utf-8")):
            elements = Elements(page).elements
            self.assertEqual(sum(tag == "script" for tag, _ in elements), 1)
            self.assertFalse(any("onerror" in attrs for _, attrs in elements))
            self.assertFalse(any(attrs.get("src") == "x" for _, attrs in elements))
        preview = (project / "preview.html").read_text(encoding="utf-8")
        embedded = re.search(r"const project=(.*?);const picker=", preview, re.DOTALL)
        self.assertIsNotNone(embedded)
        self.assertEqual(json.loads(embedded.group(1))["scenes"][0]["heading"], markup)

    def test_build_refuses_to_replace_an_existing_project(self):
        source_path, _ = self.prepare()
        brief = self.brief(source_path)
        project, _ = self.build(brief)
        original = (project / "project.json").read_bytes()
        sentinel = project / "review-notes.txt"
        sentinel.write_text("Preserve the reviewed project", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.build(brief, out=project)
        self.assertEqual((project / "project.json").read_bytes(), original)
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "Preserve the reviewed project")


class ManifestTests(OfflineCase):
    def setUp(self):
        super().setUp()
        source_path, _ = self.prepare()
        self.project, self.manifest = self.build(self.brief(source_path, [
            {"layout": "lesson", "heading": "Learn", "duration": 1.01},
            {"layout": "cta", "heading": "Practice", "duration": 1.51},
        ]))

    def test_valid_built_project_validates_without_browser(self):
        self.assertEqual(self.validate(self.project, self.manifest), (1080, 1920, 24, 62, False))

    def test_stale_scene_and_project_timing_are_rejected(self):
        self.validate(self.project, self.manifest)
        for field in ("scene_duration", "scene_frames", "scene_start", "total_frames", "total_duration"):
            with self.subTest(field=field):
                manifest = copy.deepcopy(self.manifest)
                if field == "scene_duration":
                    manifest["scenes"][0]["duration"] += 1 / manifest["fps"]
                elif field == "scene_frames":
                    manifest["scenes"][0]["frames"] += 1
                elif field == "scene_start":
                    manifest["scenes"][1]["start"] += 1 / manifest["fps"]
                elif field == "total_frames":
                    manifest["frames"] += 1
                else:
                    manifest["duration"] += 1 / manifest["fps"]
                with self.assertRaises(ValueError):
                    self.validate(self.project, manifest)

    def test_scene_path_cannot_escape_the_project(self):
        outside = self.work / "outside.html"
        outside.write_text("<!doctype html><p>Outside the immutable build</p>", encoding="utf-8")
        for invalid in ("../outside.html", str(outside)):
            with self.subTest(path=invalid):
                manifest = copy.deepcopy(self.manifest)
                manifest["scenes"][0]["file"] = invalid
                with self.assertRaises(ValueError):
                    self.validate(self.project, manifest)
        link = self.project / "scenes" / "external.html"
        link.symlink_to(outside)
        manifest = copy.deepcopy(self.manifest)
        manifest["scenes"][0]["file"] = "scenes/external.html"
        with self.assertRaises(ValueError):
            self.validate(self.project, manifest)

    def test_audio_mode_must_agree_with_tracks(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["audio_mode"] = "narrated"
        with self.assertRaises(ValueError):
            self.validate(self.project, manifest)


@unittest.skipUnless(HAS_AUDIO_TOOLS, "ffmpeg and ffprobe are required for generated local audio")
class MeasuredAudioTests(OfflineCase):
    def setUp(self):
        super().setUp()
        self.source_path, _ = self.prepare()
        self.voice = self.work / "voice.wav"
        self.voice_seconds = self.wave(self.voice, 1.137)

    def narrated_brief(self):
        return self.brief(self.source_path, [
            {"layout": "lesson", "heading": "Listen", "audio": str(self.voice),
             "narration": "我学习中文。", "duration": 0.4, "hold": 1.04},
            {"layout": "cta", "heading": "Try it", "caption": "Your turn", "duration": 1.041},
        ])

    def test_measured_audio_rounds_frames_and_preserves_hold_and_caption_bounds(self):
        project, manifest = self.build(self.narrated_brief())
        first, closing = manifest["scenes"]
        expected_frames = math.ceil((self.voice_seconds + 0.5 + 1.04) * 24)
        self.assertEqual(first["frames"], expected_frames)
        self.assertEqual(first["duration"], expected_frames / 24)
        self.assertAlmostEqual(first["audio_duration"], self.voice_seconds, places=5)
        self.assertEqual(first["audio_offset"], 0.5)
        self.assertGreaterEqual(first["duration"] - first["audio_offset"] - self.voice_seconds, 1.04)
        self.assertEqual((project / first["audio"]).read_bytes(), self.voice.read_bytes())
        self.assertEqual(closing["start"], first["duration"])
        self.assertEqual(closing["frames"], 25)
        self.assertEqual(manifest["frames"], first["frames"] + closing["frames"])
        self.assertEqual(manifest["duration"], manifest["frames"] / 24)
        self.assertEqual(manifest["audio_mode"], "narrated")
        self.assertFalse(manifest["pending_narration"])
        cues = (project / "captions.srt").read_text(encoding="utf-8").strip().split("\n\n")
        self.assertEqual(len(cues), 2)
        self.assertEqual(cues[0].splitlines(), ["1", "00:00:00,500 --> 00:00:01,637", "我学习中文。"])
        self.assertEqual(cues[1].splitlines()[2], "Your turn")
        self.assertEqual(cues[1].splitlines()[1], "00:00:03,058 --> 00:00:03,600")
        self.assertEqual(self.validate(project, manifest), (1080, 1920, 24, expected_frames + 25, True))

    def test_explicit_silent_draft_omits_voice_and_music_and_marks_pending(self):
        brief = self.narrated_brief()
        brief["bgm"] = str(self.voice)
        project, manifest = self.build(brief, silent=True)
        self.assertEqual(manifest["audio_mode"], "silent")
        self.assertTrue(manifest["pending_narration"])
        self.assertIsNone(manifest["bgm"])
        self.assertTrue(manifest["scenes"][0]["pending_narration"])
        self.assertTrue(all(scene["audio"] is None and scene["audio_duration"] == 0 for scene in manifest["scenes"]))
        self.assertFalse(any(path.suffix == ".wav" for path in (project / "assets").iterdir()))
        self.assertFalse(self.validate(project, manifest)[-1])

    def test_changed_audio_is_rejected_before_rendering(self):
        project, manifest = self.build(self.narrated_brief())
        self.validate(project, manifest)
        audio = project / manifest["scenes"][0]["audio"]
        audio.unlink()
        self.wave(audio, self.voice_seconds + 0.4)
        with self.assertRaises(ValueError):
            self.validate(project, manifest)

    def test_narration_cannot_extend_past_its_scene_or_be_declared_silent(self):
        project, manifest = self.build(self.narrated_brief())
        self.validate(project, manifest)
        for change in ("offset", "audio_mode"):
            with self.subTest(change=change):
                invalid = copy.deepcopy(manifest)
                if change == "offset":
                    invalid["scenes"][0]["audio_offset"] = invalid["scenes"][0]["duration"]
                else:
                    invalid["audio_mode"] = "silent"
                with self.assertRaises(ValueError):
                    self.validate(project, invalid)


if __name__ == "__main__":
    unittest.main()
