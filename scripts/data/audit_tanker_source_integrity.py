#!/usr/bin/env python3
"""Verify stored tanker source paragraphs are present in the saved report HTML.

This proves local transcription consistency only. It does not authenticate the
HTML download or prove that it is the publisher's current version.
"""
import csv
import hashlib
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HTML_PATH = ROOT / "data/raw/freight_rates/tanker/tanker_report_week_43_2026.html"
PARAGRAPHS_PATH = ROOT / "data/processed/freight_rates/tanker/tanker_week_43_full_paragraphs.csv"


class VisibleTextParser(HTMLParser):
    """Collect visible text while ignoring script/style/noscript content."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() in {"script", "style", "noscript"}:
            self.hidden_depth += 1

    def handle_endtag(self, tag):
        if tag.lower() in {"script", "style", "noscript"} and self.hidden_depth:
            self.hidden_depth -= 1

    def handle_data(self, data):
        if not self.hidden_depth:
            self.parts.append(data)


def normalize_text(text):
    return re.sub(r"\s+", " ", text).strip()


def audit_source(html_path=HTML_PATH, paragraphs_path=PARAGRAPHS_PATH):
    raw = html_path.read_bytes()
    parser = VisibleTextParser()
    parser.feed(raw.decode("utf-8-sig"))
    visible_text = normalize_text(" ".join(parser.parts))

    with paragraphs_path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))

    if not rows:
        raise ValueError("No extracted source paragraphs were found.")

    missing = []
    for row in rows:
        paragraph = normalize_text(row.get("full_paragraph", ""))
        if not paragraph:
            missing.append(f"paragraph {row.get('paragraph_number', '?')}: empty")
        elif paragraph not in visible_text:
            missing.append(
                f"paragraph {row.get('paragraph_number', '?')}: not present in saved HTML"
            )

    return {
        "html_sha256": hashlib.sha256(raw).hexdigest(),
        "paragraph_count": len(rows),
        "matched_paragraph_count": len(rows) - len(missing),
        "missing": missing,
    }


def main():
    result = audit_source()
    print(f"Saved HTML SHA-256: {result['html_sha256']}")
    print(f"Extracted paragraphs: {result['paragraph_count']}")
    print(f"Paragraphs found in saved HTML: {result['matched_paragraph_count']}")
    print(f"Missing/empty paragraphs: {len(result['missing'])}")
    for item in result["missing"][:50]:
        print("SOURCE ERROR:", item)
    if result["missing"]:
        print("FAIL: local source transcription does not match the saved HTML.")
        return 1
    print("PASS: extracted paragraphs are present in saved HTML.")
    print("LIMIT: this does not authenticate the HTML or independently verify numeric interpretations.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
