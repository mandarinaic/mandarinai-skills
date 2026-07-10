#!/usr/bin/env python3
"""Extract an EPUB's text in reading order. Stdlib only — no dependencies.

Usage: python3 extract-epub.py <book.epub> [out.txt]
       (no out.txt -> print to stdout)

Reads META-INF/container.xml -> OPF manifest/spine -> concatenates each
chapter's text with chapter separators, so grep line numbers map to one file.
"""

import re
import sys
import zipfile
import posixpath
from html.parser import HTMLParser
from xml.etree import ElementTree as ET


class TextExtractor(HTMLParser):
    SKIP = {"script", "style"}
    BLOCK = {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr",
             "br", "blockquote", "section", "article", "td"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip:
            self._skip -= 1
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)

    def text(self):
        out = "".join(self.parts)
        out = re.sub(r"[ \t]+", " ", out)
        out = re.sub(r"\n\s*\n+", "\n\n", out)
        return out.strip()


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__.strip())
    epub_path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else None

    z = zipfile.ZipFile(epub_path)
    ns = {
        "c": "urn:oasis:names:tc:opendocument:xmlns:container",
        "opf": "http://www.idpf.org/2007/opf",
    }
    container = ET.fromstring(z.read("META-INF/container.xml"))
    opf_path = container.find(".//c:rootfile", ns).get("full-path")
    opf_dir = posixpath.dirname(opf_path)
    opf = ET.fromstring(z.read(opf_path))

    manifest = {
        item.get("id"): item.get("href")
        for item in opf.findall(".//opf:manifest/opf:item", ns)
    }
    spine_ids = [ref.get("idref") for ref in opf.findall(".//opf:spine/opf:itemref", ns)]

    title_el = opf.find(".//{http://purl.org/dc/elements/1.1/}title")
    chunks = []
    if title_el is not None and title_el.text:
        chunks.append(f"# {title_el.text.strip()}\n")

    for idx, sid in enumerate(spine_ids, 1):
        href = manifest.get(sid)
        if not href or not re.search(r"\.x?html?$", href, re.I):
            continue
        full = posixpath.normpath(posixpath.join(opf_dir, href)) if opf_dir else href
        try:
            raw = z.read(full).decode("utf-8", errors="replace")
        except KeyError:
            continue
        parser = TextExtractor()
        parser.feed(raw)
        text = parser.text()
        if text:
            chunks.append(f"\n\n===== [{idx:03d}] {href} =====\n\n{text}")

    result = "".join(chunks).strip() + "\n"
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(result)
        chars = len(result)
        print(f"OK: {out_path} ({chars} chars, ~{chars // 600} 千字 if Chinese)")
    else:
        sys.stdout.write(result)


if __name__ == "__main__":
    main()
