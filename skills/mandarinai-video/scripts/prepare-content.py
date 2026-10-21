#!/usr/bin/env python3
"""Create an immutable video source bundle from one Goose content detail.

Uses public GET requests only. It never reads project credentials, uploads media,
or publishes content. Saved private author exports can be normalized locally.
"""

import argparse
import ipaddress
import json
import os
from pathlib import Path
import re
import sys
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


DEFAULT_ORIGIN = "https://www.mandarinai.com"
MAX_RESPONSE_BYTES = 10 * 1024 * 1024
SUPPORTED_SITE_LOCALES = {"en", "es", "fr", "ar", "ru", "zh"}
DETAIL_ROUTES = {
    "word": "/hsk/word/detail/{id}",
    "grammar": "/grammar/detail/{id}",
    "university": "/university/detail/{id}",
    "article": "/tools/articles/{id}",
}
LIBRARY_ROUTES = {
    "word": "/hsk/word/list/1",
    "grammar": "/grammar/list/1",
    "university": "/university/list/1",
    "article": "/tools/articles",
}
CONTENT_FIELDS = {
    "word": (
        "word", "word_t", "pinyin", "zhuyin", "hsk_level", "hsk_level_legacy",
        "part_of_speech", "english", "meaning", "meanings", "image", "audio",
        "video", "examples", "structured_examples", "download_example", "synonyms",
        "antonyms", "homographs", "same_level_words", "measure_words", "graph_data",
        "meaning_quiz_options", "updated_at",
    ),
    "grammar": (
        "title", "english_title", "hsk_level", "summary", "abstract", "images",
        "audio_url", "content_groups", "content", "english",
    ),
    "university": (
        "name", "en_name", "alias", "country_id", "country", "province_id",
        "province", "city_id", "city", "founded_year", "address", "en_address",
        "funding", "languages", "semesters", "logo", "thumbnail", "images",
        "videos", "intro", "website", "admission_url", "campuses", "degree_levels",
        "update_time",
    ),
    "article": (
        "title", "thumbnail", "original_text", "chinese_text", "metadata", "sentences",
        "content_blocks", "grammar_points", "is_public", "user_id", "author_id",
        "user", "created_at", "create_time",
    ),
}


def origin(value):
    """Validate an HTTP(S) origin, excluding credentials, paths and query text."""
    if not value or re.search(r"[\s\\%]", value) or any(ord(c) < 32 for c in value):
        raise ValueError("base URL must be an HTTP(S) origin without whitespace or escapes")
    try:
        parsed = urlsplit(value)
        host = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise ValueError("invalid base URL host or port") from exc
    if (parsed.scheme not in {"http", "https"} or not host or parsed.username is not None
            or parsed.password is not None or parsed.path not in {"", "/"}
            or parsed.query or parsed.fragment or "?" in value or "#" in value):
        raise ValueError("base URL must be an HTTP(S) origin without credentials, path, query or fragment")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        labels = host.rstrip(".").split(".")
        if (len(host) > 253 or not all(re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", label)
                                       for label in labels)):
            raise ValueError("invalid base URL hostname")
    if port is not None and not 1 <= port <= 65535:
        raise ValueError("invalid base URL port")
    return urlunsplit((parsed.scheme, parsed.netloc.lower(), "", "", ""))


def content_id(value):
    # JSON integers keep their exact Python precision. Never pass IDs through float.
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError("detail id must be a string or integer, never a float")
    result = str(value)
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", result):
        raise ValueError("id must contain only letters, digits, underscores or hyphens")
    return result


def parse_json(text):
    def invalid_constant(value):
        raise ValueError("non-finite JSON number: " + value)
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("ambiguous JSON contains duplicate field: " + key)
            result[key] = value
        return result
    try:
        return json.loads(text, parse_constant=invalid_constant, object_pairs_hook=unique_object)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("input is not valid JSON: " + str(exc)) from exc


def detail_record(payload, requested_id):
    if not isinstance(payload, dict):
        raise ValueError("expected one JSON detail object, not a list or scalar")
    if "code" in payload:
        if type(payload["code"]) is not int or payload["code"] != 200:
            raise ValueError("unsuccessful API envelope; expected integer code 200")
        if "data" not in payload or "id" in payload:
            raise ValueError("API envelope has missing or ambiguous data")
        record = payload["data"]
    elif "data" in payload:
        raise ValueError("ambiguous data wrapper; expected code 200 and direct data object")
    else:
        record = payload
    if not isinstance(record, dict) or "id" not in record:
        raise ValueError("expected a direct detail with id; list and result wrappers are unsupported")
    if "list" in record or "result" in record:
        raise ValueError("ambiguous detail object contains a list or result wrapper")
    actual_id = content_id(record["id"])
    if actual_id != requested_id:
        raise ValueError("detail id mismatch: requested " + requested_id + ", received " + actual_id)
    if "is_public" in record and not isinstance(record["is_public"], bool):
        raise ValueError("is_public must be a JSON boolean when present")
    return record


def api_url(kind, requested_id, language, base):
    if not re.fullmatch(r"[1-9][0-9]*", requested_id):
        raise ValueError("public API requests require a positive decimal id; demo ids are local only")
    if kind == "word":
        path = "/api/word/hsk/get"
        query = {"id": requested_id, "language": language,
                 "include": "examples,download,relations,quiz"}
    elif kind == "grammar":
        path, query = "/api/grammar/get", {"id": requested_id}
    elif kind == "university":
        path, query = "/api/university/get", {"id": requested_id}
    else:
        path, query = "/api/article/processed/" + requested_id, {"lang": language}
    return base + path + "?" + urlencode(query)


class SameOriginRedirects(HTTPRedirectHandler):
    def __init__(self, allowed_origin):
        self.allowed_origin = allowed_origin

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urlsplit(newurl)
        redirected_origin = origin(urlunsplit((parsed.scheme, parsed.netloc, "", "", "")))
        if redirected_origin != self.allowed_origin:
            raise ValueError("refusing redirect to a different API origin")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url, base):
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "MandarinAI-Video-Source/1.0"}, method="GET")
    try:
        with build_opener(SameOriginRedirects(base)).open(request, timeout=20) as response:
            body = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as exc:
        raise ValueError("public content request failed with HTTP " + str(exc.code)) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise ValueError("public content request failed: " + str(exc)) from exc
    if len(body) > MAX_RESPONSE_BYTES:
        raise ValueError("API response exceeds the 10 MiB limit")
    try:
        return parse_json(body.decode("utf-8-sig"))
    except UnicodeDecodeError as exc:
        raise ValueError("API response is not UTF-8 JSON") from exc


def nonempty_text(record, key):
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError("missing nonempty " + key + " in source detail")
    return value.strip()


def normalized_content(kind, record):
    def array(value, label):
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError(label + " must be an array")
        return value

    def objects(value, label):
        items = array(value, label)
        if not all(isinstance(item, dict) for item in items):
            raise ValueError(label + " must contain objects")
        return items

    def strings(value, label):
        items = array(value, label)
        if not all(isinstance(item, str) for item in items):
            raise ValueError(label + " must contain strings")
        return items

    content = {key: record[key] for key in CONTENT_FIELDS[kind] if key in record}
    if kind == "word":
        for example in objects(record.get("structured_examples"), "structured_examples"):
            if example.get("translations") is not None and not isinstance(example["translations"], dict):
                raise ValueError("word example translations must be a language-to-text object")
        # Prefer structured examples; the original legacy field remains in raw.
        if record.get("structured_examples"):
            content["examples"] = record["structured_examples"]
        if record.get("hsk_level") == 7:
            content["hsk_level_label"] = "7–9"
    if kind == "grammar":
        strings(record.get("images"), "grammar images")
        for group in objects(record.get("content_groups"), "content_groups"):
            for sentence in objects(group.get("sentences"), "grammar sentences"):
                objects(sentence.get("translations"), "grammar sentence translations")
    if kind == "university":
        gallery = []
        candidates = list(strings(record.get("images"), "university images"))
        for campus in objects(record.get("campuses"), "university campuses"):
            candidates.extend(strings(campus.get("images"), "campus images"))
        for item in candidates:
            if isinstance(item, str) and item and item not in gallery:
                gallery.append(item)
        content["gallery"] = gallery
    if kind == "article":
        for sentence in objects(record.get("sentences"), "article sentences"):
            objects(sentence.get("translations"), "article sentence translations")
            for segment in objects(sentence.get("word_segments"), "word_segments"):
                word_info = segment.get("word_info")
                if word_info is not None:
                    if not isinstance(word_info, dict):
                        raise ValueError("word_info must be an object")
                    objects(word_info.get("translations"), "word_info translations")
        objects(record.get("content_blocks"), "content_blocks")
        objects(record.get("grammar_points"), "grammar_points")
    return content


def prepare(args):
    requested_id = content_id(args.id)
    if not re.fullmatch(r"[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})?", args.language):
        raise ValueError("language must be a language code such as en, es or zh")
    site = origin(args.site_base or os.environ.get("MANDARIN_SITE_BASE") or DEFAULT_ORIGIN)
    output = Path(args.out)
    if output.exists() or output.is_symlink():
        raise ValueError("output already exists; choose a new --out path")
    fetched_url = None
    if args.input:
        try:
            payload = parse_json(Path(args.input).read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeDecodeError) as exc:
            raise ValueError("cannot read saved JSON: " + str(exc)) from exc
        provenance = {"method": "file", "input": Path(args.input).name}
    else:
        base = origin(args.api_base or os.environ.get("MANDARIN_API_BASE") or DEFAULT_ORIGIN)
        fetched_url = api_url(args.kind, requested_id, args.language, base)
        payload = fetch(fetched_url, base)
        provenance = {"method": "api"}
    record = detail_record(payload, requested_id)
    private = record.get("is_public") is False
    if fetched_url and private:
        raise ValueError("public API returned explicitly private content; use an authorized saved export locally")
    provenance["visibility"] = "private" if private else "public" if record.get("is_public") is True else "unspecified"
    fixture = record.get("_fixture", payload.get("_fixture"))
    synthetic = isinstance(fixture, dict) and fixture.get("synthetic") is True
    if synthetic:
        provenance["synthetic"] = True
        if isinstance(fixture.get("note"), str):
            provenance["note"] = fixture["note"]
    title_key = {"word": "word", "grammar": "title", "university": "name", "article": "title"}[args.kind]
    title = nonempty_text(record, title_key)
    prefix = "/" + args.language if args.language in SUPPORTED_SITE_LOCALES - {"en"} else ""
    route = LIBRARY_ROUTES[args.kind] if synthetic else DETAIL_ROUTES[args.kind].format(id=requested_id)
    bundle = {
        "kind": args.kind, "id": requested_id, "title": title,
        "url": site + prefix + route, "language": args.language,
        "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "content": normalized_content(args.kind, record), "raw": record,
        "provenance": provenance,
    }
    if fetched_url:
        bundle["api_url"] = fetched_url
    encoded = json.dumps(bundle, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output.open("x", encoding="utf-8") as handle:
            handle.write(encoded)
    except FileExistsError as exc:
        raise ValueError("output already exists; choose a new --out path") from exc
    print(str(output))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", required=True, choices=tuple(DETAIL_ROUTES))
    parser.add_argument("--id", required=True, help="Exact content ID, preserved as a string")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--input", help="Saved bare detail or code-200/data JSON envelope")
    source.add_argument("--api-base", help="Public HTTP(S) API origin; default MANDARIN_API_BASE or production")
    parser.add_argument("--site-base", help="Swan HTTP(S) origin; default MANDARIN_SITE_BASE or production")
    parser.add_argument("--language", default="en", help="Translation language; default en")
    parser.add_argument("--out", required=True, help="New JSON path; existing outputs are never overwritten")
    args = parser.parse_args()
    try:
        prepare(args)
    except (ValueError, OSError) as exc:
        parser.exit(2, "error: " + str(exc) + "\n")


if __name__ == "__main__":
    main()
