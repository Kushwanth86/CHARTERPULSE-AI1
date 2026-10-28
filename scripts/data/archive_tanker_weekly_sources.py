#!/usr/bin/env python3
"""Archive official Baltic Exchange tanker reports for historical validation.

This archives publisher-hosted HTML and extracts route-bearing paragraphs. It
does not convert text into numeric observations or mark values as verified.
"""
import argparse
import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data/raw/freight_rates/tanker"
PROCESSED_DIR = ROOT / "data/processed/freight_rates/tanker"
BASE_URL = "https://www.balticexchange.com/en/data-services/WeeklyRoundup/tanker/news/2026/tanker-report-week-{week}.html"
REPORT_DATES = {40: "2026-10-02", 41: "2026-10-09", 42: "2026-10-16", 43: "2026-10-23"}
ROUTE_RE = re.compile(r"(?<![A-Z0-9])(?:TC|TD)\d{1,3}[A-Z]?(?![A-Z0-9])", re.I)


def normalize_text(text):
    return re.sub(r"\s+", " ", text).strip()


class ReportParser(HTMLParser):
    """Extract page-visible text and paragraph text without script/style noise."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden_depth = 0
        self.paragraph_depth = 0
        self.paragraph_parts = []
        self.paragraphs = []
        self.visible_parts = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in {"script", "style", "noscript"}:
            self.hidden_depth += 1
        if tag == "p" and not self.hidden_depth:
            self.paragraph_depth += 1
            if self.paragraph_depth == 1:
                self.paragraph_parts = []

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "p" and self.paragraph_depth:
            self.paragraph_depth -= 1
            if self.paragraph_depth == 0:
                paragraph = normalize_text(" ".join(self.paragraph_parts))
                if paragraph:
                    self.paragraphs.append(paragraph)
        if tag in {"script", "style", "noscript"} and self.hidden_depth:
            self.hidden_depth -= 1

    def handle_data(self, data):
        if self.hidden_depth:
            return
        self.visible_parts.append(data)
        if self.paragraph_depth:
            self.paragraph_parts.append(data)


def parse_report(raw_html, week):
    parser = ReportParser()
    parser.feed(raw_html.decode("utf-8-sig", errors="replace"))
    visible = normalize_text(" ".join(parser.visible_parts))
    title_pattern = re.compile(rf"Tanker\s+report\s*[-–—]\s*Week\s+{week}\b", re.I)
    if not title_pattern.search(visible):
        raise ValueError(f"Official page does not identify itself as Tanker report Week {week}; visible preview={visible[:240]!r}")
    paragraphs = [p for p in parser.paragraphs if ROUTE_RE.search(p)]
    if len(paragraphs) < 5:
        raise ValueError(f"Week {week}: only {len(paragraphs)} route-bearing paragraphs found; refusing archive")
    return paragraphs


def fetch_week(week, opener=urlopen, now=None):
    if week not in REPORT_DATES:
        raise ValueError(f"Unsupported 2026 report week: {week}")
    url = BASE_URL.format(week=week)
    request = Request(url, headers={"User-Agent": "CharterPulseAI-source-audit/1.0"})
    with opener(request, timeout=30) as response:
        status = getattr(response, "status", 200)
        if status != 200:
            raise RuntimeError(f"Week {week}: publisher returned HTTP {status}")
        raw_html = response.read()
    paragraphs = parse_report(raw_html, week)
    digest = hashlib.sha256(raw_html).hexdigest()
    fetched_at = (now or datetime.now(timezone.utc)).isoformat()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = RAW_DIR / f"tanker_report_week_{week}_2026.html"
    csv_path = PROCESSED_DIR / f"tanker_week_{week}_full_paragraphs.csv"
    manifest_path = PROCESSED_DIR / f"tanker_week_{week}_source_manifest.json"
    raw_path.write_bytes(raw_html)
    with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=[
            "report_date", "report_week", "paragraph_number", "route_codes",
            "full_paragraph", "source_url", "source_file", "source_sha256",
            "fetched_at_utc", "review_status",
        ])
        writer.writeheader()
        for number, paragraph in enumerate(paragraphs, start=1):
            routes = sorted({match.upper() for match in ROUTE_RE.findall(paragraph)})
            writer.writerow({
                "report_date": REPORT_DATES[week],
                "report_week": f"2026-W{week:02d}",
                "paragraph_number": number,
                "route_codes": ";".join(routes),
                "full_paragraph": paragraph,
                "source_url": url,
                "source_file": raw_path.name,
                "source_sha256": digest,
                "fetched_at_utc": fetched_at,
                "review_status": "REVIEW_REQUIRED_SOURCE_ARCHIVE",
            })
    manifest = {
        "report_week": f"2026-W{week:02d}",
        "report_date": REPORT_DATES[week],
        "source_url": url,
        "source_file": str(raw_path.relative_to(ROOT)),
        "paragraph_file": str(csv_path.relative_to(ROOT)),
        "sha256": digest,
        "fetched_at_utc": fetched_at,
        "route_paragraph_count": len(paragraphs),
        "status": "SOURCE_ARCHIVED_NOT_NUMERICALLY_VERIFIED",
        "limitations": [
            "SHA-256 identifies downloaded bytes but is not a publisher signature.",
            "Paragraph extraction does not verify numeric interpretation or observation mapping.",
            "Human review is required before converting paragraphs into forecast inputs.",
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weeks", nargs="+", type=int, default=[40, 41, 42, 43])
    args = parser.parse_args(argv)
    failures = 0
    for week in args.weeks:
        try:
            result = fetch_week(week)
            print(f"ARCHIVED {result['report_week']}: {result['route_paragraph_count']} paragraphs; sha256={result['sha256']}")
        except (HTTPError, URLError, TimeoutError, OSError, ValueError, RuntimeError) as exc:
            failures += 1
            print(f"FAIL Week {week}: {exc}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
