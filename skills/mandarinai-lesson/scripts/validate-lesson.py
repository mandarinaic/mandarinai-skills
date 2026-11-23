#!/usr/bin/env python3
"""Validate authoring lesson v1 without network access or third-party packages."""
import argparse
from collections import Counter
import json
from pathlib import Path
import unicodedata


def normalize_text(value, policy):
    if policy.get("nfkc"):
        value = unicodedata.normalize("NFKC", value)
    ignored = policy.get("ignore_punctuation", "")
    if policy.get("nfkc"):
        ignored = unicodedata.normalize("NFKC", ignored)
    return "".join(c for c in value if c not in ignored and not (
        policy.get("ignore_whitespace") and c.isspace()))


def validate(data):
    errors = []

    def require(condition, message):
        if not condition:
            errors.append(message)
        return bool(condition)

    def string(value):
        return isinstance(value, str) and bool(value.strip())

    def localized(value):
        return isinstance(value, dict) and string(value.get("en")) and all(
            string(k) and string(v) for k, v in value.items())

    def rows(value, path):
        if not require(isinstance(value, list) and bool(value), f"{path}: expected nonempty array"):
            return []
        result = [v for v in value if isinstance(v, dict)]
        require(len(result) == len(value), f"{path}: every row must be an object")
        ids = [v.get("id") for v in result]
        require(all(string(v) for v in ids), f"{path}: nonempty string IDs required")
        valid_ids = [v for v in ids if isinstance(v, str)]
        require(len(set(valid_ids)) == len(valid_ids), f"{path}: duplicate IDs")
        return result

    def refs(value, allowed, path, nonempty=True):
        if not require(isinstance(value, list), f"{path}: expected an array of IDs"):
            return []
        require(not nonempty or bool(value), f"{path}: expected at least one ID")
        valid = [v for v in value if isinstance(v, str)]
        require(len(valid) == len(value), f"{path}: IDs must be strings")
        require(len(set(valid)) == len(valid), f"{path}: duplicate references")
        for v in valid:
            require(v in allowed, f"{path}: unknown ID {v}")
        return valid

    if not require(isinstance(data, dict), "lesson: expected an object"):
        return errors
    require(type(data.get("schema_version")) is int and data["schema_version"] == 1,
            "schema_version: expected 1")
    for key in ("id", "version", "course_id"):
        require(string(data.get(key)), f"{key}: nonempty string required")
    require(localized(data.get("title")), "title: English text and valid locale map required")
    if "description" in data:
        require(localized(data["description"]), "description: valid locale map required")
    level = data.get("level", {})
    require(isinstance(level, dict) and string(level.get("label")), "level: label required")
    if isinstance(level, dict):
        if "prerequisites" in level:
            require(isinstance(level["prerequisites"], list) and all(string(v) for v in
                    level["prerequisites"]), "level.prerequisites: string array required")
        if "estimated_minutes" in level:
            require(type(level["estimated_minutes"]) in (int, float) and
                    0 < level["estimated_minutes"] < float("inf"),
                    "level.estimated_minutes: finite positive number required")
    editorial = data.get("editorial", {})
    require(isinstance(editorial, dict) and editorial.get("status") in ("draft", "reviewed"),
            "editorial.status: draft or reviewed required")
    sources = rows(data.get("sources"), "sources")
    objectives = rows(data.get("objectives"), "objectives")
    vocabulary = rows(data.get("vocabulary"), "vocabulary")
    patterns = rows(data.get("patterns"), "patterns")
    dialogue = rows(data.get("dialogue"), "dialogue")
    questions = rows(data.get("questions"), "questions")
    flow = rows(data.get("flow"), "flow")
    idset = lambda values: {v["id"] for v in values if string(v.get("id"))}
    source_ids, objective_ids = idset(sources), idset(objectives)
    vocab_ids, pattern_ids, question_ids = idset(vocabulary), idset(patterns), idset(questions)

    for s in sources:
        path = f"source {s.get('id')}"
        require(s.get("role") in ("original", "topic-reference"), f"{path}: invalid role")
        for key in ("title", "verification", "rights"):
            require(string(s.get(key)), f"{path}: {key} required")
        for key in ("pdf_pages", "printed_pages"):
            if key in s:
                require(isinstance(s[key], list) and bool(s[key]) and all(
                    type(n) is int and n > 0 for n in s[key]), f"{path}: {key} must be positive page numbers")
    evidence = {}
    skills = {"meaning", "comprehension", "word-order", "production", "interaction"}
    for o in objectives:
        path = f"objective {o.get('id')}"
        require(localized(o.get("can_do")), f"{path}: can_do text required")
        rule = o.get("evidence", {})
        if not require(isinstance(rule, dict), f"{path}: evidence object required"):
            continue
        required = refs(rule.get("exit_skills"), skills, f"{path}.evidence.exit_skills")
        require(rule.get("retention_requires_delayed_review") is True,
                f"{path}: retention must require delayed review")
        if string(o.get("id")):
            evidence[o["id"]] = required
    for v in vocabulary:
        for key in ("zh", "pinyin"):
            require(string(v.get(key)), f"vocabulary {v.get('id')}: {key} required")
        require(localized(v.get("translations")), f"vocabulary {v.get('id')}: translation required")
    for p in patterns:
        require(string(p.get("pattern")) and localized(p.get("explanation")),
                f"pattern {p.get('id')}: pattern and explanation required")
        example = p.get("example", {})
        require(isinstance(example, dict) and all(string(example.get(k)) for k in
                ("zh", "pinyin")) and localized(example.get("translations")),
                f"pattern {p.get('id')}: complete example required")
    for turn in dialogue:
        require(all(string(turn.get(k)) for k in ("speaker", "zh", "pinyin")) and
                localized(turn.get("translations")), f"dialogue {turn.get('id')}: incomplete turn")

    prompts = set()
    for q in questions:
        path = f"question {q.get('id')}"
        for field, allowed, nonempty in (("objective_ids", objective_ids, True),
                ("vocabulary_ids", vocab_ids, False), ("pattern_ids", pattern_ids, False),
                ("source_ids", source_ids, True)):
            refs(q.get(field), allowed, f"{path}.{field}", nonempty)
        require(q.get("phase") in ("practice", "mission", "exit"), f"{path}: invalid phase")
        require(isinstance(q.get("skill"), str) and q["skill"] in skills, f"{path}: invalid skill")
        require(q.get("skill") != "production" or q.get("type") == "text",
                f"{path}: production evidence requires a typed response")
        require(q.get("skill") != "word-order" or q.get("type") == "order",
                f"{path}: word-order evidence requires ordered chunks")
        require(type(q.get("difficulty")) is int and 1 <= q["difficulty"] <= 5,
                f"{path}: difficulty must be 1–5")
        if require(localized(q.get("prompt")), f"{path}: prompt required"):
            prompt_key = " ".join(unicodedata.normalize("NFKC", q["prompt"]["en"]).casefold().split())
            require(prompt_key not in prompts, f"{path}: repeated prompt; exit checks need new prompts")
            prompts.add(prompt_key)
        require(localized(q.get("hint")), f"{path}: hint required")
        feedback = q.get("feedback", {})
        require(isinstance(feedback, dict) and all(localized(feedback.get(k)) for k in
                ("correct", "incorrect")), f"{path}: correct and incorrect feedback required")
        answer = q.get("answer", {})
        if not require(isinstance(answer, dict), f"{path}: answer object required"):
            continue
        if q.get("type") == "choice":
            options = rows(q.get("options"), f"{path}.options")
            require(len(options) >= 2, f"{path}: at least two options required")
            require(string(answer.get("option_id")) and answer["option_id"] in idset(options),
                    f"{path}: answer must reference an option ID")
            texts = []
            for option in options:
                text = option.get("text")
                require(string(text), f"{path}: option text required")
                require(localized(option.get("feedback")), f"{path}: per-option rationale required")
                if isinstance(text, str):
                    texts.append(normalize_text(text, {"nfkc": True, "ignore_whitespace": True,
                                  "ignore_punctuation": "，。！？、,.!?"}))
            require(len(set(texts)) == len(texts), f"{path}: indistinguishable option text")
        elif q.get("type") == "order":
            chunks = rows(q.get("chunks"), f"{path}.chunks")
            require(len(chunks) >= 2, f"{path}: at least two chunks required")
            require(all(string(c.get("text")) for c in chunks), f"{path}: chunk text required")
            order = refs(answer.get("chunk_ids"), idset(chunks), f"{path}.answer.chunk_ids")
            require(set(order) == idset(chunks), f"{path}: answer must use each chunk exactly once")
        elif q.get("type") == "text":
            accepted, policy = answer.get("accepted"), answer.get("normalization")
            if not require(isinstance(accepted, list) and bool(accepted) and all(string(a) for a in accepted),
                           f"{path}: accepted text variants required"):
                continue
            if not require(isinstance(policy, dict) and set(policy) == {
                "nfkc", "ignore_whitespace", "ignore_punctuation"} and
                type(policy.get("nfkc")) is bool and type(policy.get("ignore_whitespace")) is bool and
                isinstance(policy.get("ignore_punctuation"), str), f"{path}: explicit normalization required"):
                continue
            require(all(unicodedata.category(c).startswith("P") for c in policy["ignore_punctuation"]),
                    f"{path}: only punctuation may be ignored, not letters, numbers or symbols")
            normalized = [normalize_text(a, policy) for a in accepted]
            require(all(normalized) and len(set(normalized)) == len(normalized),
                    f"{path}: empty or equivalent accepted variants")
        else:
            require(False, f"{path}: supported types are choice, order and text")

    used = []
    by_id = {q["id"]: q for q in questions if string(q.get("id"))}
    for step in flow:
        path = f"flow {step.get('id')}"
        require(localized(step.get("title")), f"{path}: title required")
        ids = refs(step.get("question_ids"), question_ids, f"{path}.question_ids")
        for qid in ids:
            if qid in by_id:
                require(step.get("phase") == by_id[qid].get("phase"), f"{path}: phase mismatch for {qid}")
        used.extend(ids)
    require(Counter(used) == Counter(question_ids), "flow: use every question exactly once")
    for oid, required_skills in evidence.items():
        available = {q.get("skill") for q in questions if q.get("phase") == "exit" and
                     isinstance(q.get("objective_ids"), list) and oid in q["objective_ids"] and
                     isinstance(q.get("skill"), str)}
        for skill in required_skills:
            require(skill in available, f"objective {oid}: no exit question for {skill}")
    review = data.get("review", {})
    require(isinstance(review, dict) and string(review.get("scope")) and string(review.get("policy")) and
            type(review.get("suggested_delay_days")) is int and review["suggested_delay_days"] > 0,
            "review: explicit scope, delayed policy and positive delay required")
    return errors


def load_lesson(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    errors = validate(data)
    if errors:
        raise ValueError("\n".join(errors))
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lesson", type=Path)
    args = parser.parse_args()
    try:
        data = load_lesson(args.lesson)
    except (ValueError, OSError) as error:
        parser.exit(1, f"Invalid lesson:\n{error}\n")
    print(f"Valid: {data['id']} v{data['version']}; {len(data['objectives'])} objectives, "
          f"{len(data['questions'])} questions. Editorial status: {data['editorial']['status']}.")


if __name__ == "__main__":
    main()
