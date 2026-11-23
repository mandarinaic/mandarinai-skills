import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


validator = module("lesson_validator", "validate-lesson.py")
builder = module("lesson_builder", "build-preview.py")
FIXTURE = ROOT / "examples/breakfast-order.lesson.json"


class LessonTests(unittest.TestCase):
    def setUp(self):
        self.lesson = json.loads(FIXTURE.read_text())

    def test_original_pilot_has_complete_assessment_links(self):
        self.assertEqual(validator.validate(self.lesson), [])

    def test_unknown_item_reference_cannot_silently_expand_scope(self):
        self.lesson["questions"][0]["vocabulary_ids"].append("unrelated-hsk-item")
        self.assertTrue(any("unknown ID unrelated-hsk-item" in e for e in validator.validate(self.lesson)))

    def test_normalization_handles_punctuation_without_erasing_meaning(self):
        policy = self.lesson["questions"][2]["answer"]["normalization"]
        self.assertEqual(validator.normalize_text(" 多少钱？ ", policy), "多少钱")
        self.assertNotEqual(validator.normalize_text("多少￥钱", policy), "多少钱")
        self.assertNotEqual(validator.normalize_text("多钱", policy), "多少钱")

    def test_equivalent_text_answers_are_rejected(self):
        self.lesson["questions"][2]["answer"]["accepted"].append("多少钱？")
        self.assertTrue(any("equivalent accepted" in e for e in validator.validate(self.lesson)))

    def test_normalization_cannot_ignore_meaningful_characters(self):
        self.lesson["questions"][2]["answer"]["normalization"]["ignore_punctuation"] = "多￥"
        self.assertTrue(any("only punctuation" in e for e in validator.validate(self.lesson)))

    def test_duplicate_visible_options_are_ambiguous(self):
        self.lesson["questions"][0]["options"][1]["text"] = "Ordering two buns。"
        self.assertTrue(any("indistinguishable" in e for e in validator.validate(self.lesson)))

    def test_order_answer_cannot_reuse_a_chunk(self):
        self.lesson["questions"][1]["answer"]["chunk_ids"][-1] = "two"
        self.assertTrue(any("each chunk exactly once" in e for e in validator.validate(self.lesson)))

    def test_exit_check_requires_each_stated_evidence_skill(self):
        self.lesson["questions"][-1]["skill"] = "meaning"
        self.assertTrue(any("no exit question for interaction" in e for e in validator.validate(self.lesson)))

    def test_every_question_must_be_reachable_once(self):
        self.lesson["flow"][0]["question_ids"].pop()
        self.assertIn("flow: use every question exactly once", validator.validate(self.lesson))

    def test_bad_nested_input_reports_validation_errors(self):
        self.lesson["questions"][0]["answer"] = []
        self.lesson["objectives"][0]["evidence"] = None
        self.assertGreaterEqual(len(validator.validate(self.lesson)), 2)

    def test_invalid_optional_level_fields_cannot_crash_preview(self):
        self.lesson["level"]["prerequisites"] = "Know numbers"
        self.lesson["level"]["estimated_minutes"] = True
        errors = validator.validate(self.lesson)
        self.assertTrue(any("prerequisites: string array" in e for e in errors))
        self.assertTrue(any("estimated_minutes: finite positive" in e for e in errors))

    def test_choice_is_not_typed_production_evidence(self):
        self.lesson["questions"][-1]["skill"] = "production"
        self.assertTrue(any("production evidence requires" in e for e in validator.validate(self.lesson)))

    def test_embedded_source_text_cannot_end_the_data_script(self):
        with tempfile.TemporaryDirectory() as directory:
            lesson = copy.deepcopy(self.lesson)
            lesson["title"]["en"] = "</script><script>alert(1)</script>"
            source, output = Path(directory) / "input.json", Path(directory) / "preview.html"
            source.write_text(json.dumps(lesson))
            builder.build(source, output)
            html = output.read_text()
            self.assertNotIn(lesson["title"]["en"], html)
            self.assertIn("\\u003c/script\\u003e", html)
            with self.assertRaises(FileExistsError):
                builder.build(source, output)


if __name__ == "__main__":
    unittest.main()
