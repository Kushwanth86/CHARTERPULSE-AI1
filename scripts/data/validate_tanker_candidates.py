
#!/usr/bin/env python3
"""Validate the local Week 43 tanker candidate CSV against extracted source paragraphs.

Read-only: does not change data or connect to Supabase.

A PASS means structural and source-token checks passed. It does not establish
that every value, qualifier, or interpretation has been independently verified.
"""

import csv
import json
import re
import sys
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "data/processed/freight_rates/tanker"
PARAGRAPHS = BASE / "tanker_week_43_full_paragraphs.csv"
CANDIDATES = BASE / "tanker_week_43_normalized_candidates.csv"
REPORT = BASE / "tanker_week_43_normalization_report.json"

EXPECTED_ROWS = 51
EXPECTED_ROUTES = 26
REVIEW_STATUS = "REVIEW_REQUIRED_SINGLE_WEEK"

ALLOWED_VALUE_QUALIFIERS = {
    "exact",
    "rounded",
    "about",
    "just_under",
    "just_over",
    "almost",
    "over",
    "under",
}

ALLOWED_CHANGE_QUALIFIERS = ALLOWED_VALUE_QUALIFIERS | {"approximate"}

ALLOWED_UNITS = {
    "worldscale_assessment": {"WS_points"},
    "tce_earnings": {"USD_per_day"},
    "voyage_rate": {"USD_per_voyage"},
}

REQUIRED_FIELDS = {
    "report_date",
    "report_week",
    "source",
    "source_url",
    "source_file",
    "provenance",
    "review_status",
    "route_code",
    "vessel_class",
    "route_description",
    "metric",
    "value",
    "unit",
    "value_qualifier",
    "weekly_change_value",
    "weekly_change_unit",
    "weekly_change_qualifier",
    "source_text",
}

OPTIONAL_CHANGE_FIELDS = {
    "weekly_change_value",
    "weekly_change_unit",
    "weekly_change_qualifier",
}


def normalize(text):
    """Normalize whitespace and common dash variants for text comparisons."""
    text = (text or "").replace("\u00a0", " ").replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", text).strip().casefold()


def dec(text):
    """Parse a decimal value, accepting thousands separators."""
    try:
        return Decimal((text or "").strip().replace(",", ""))
    except (InvalidOperation, AttributeError):
        return None


def variants(text, metric):
    """Generate source-style numeric tokens for matching candidate values."""
    n = dec(text)
    if n is None:
        return set()

    n = abs(n)
    plain = format(n, "f")
    out = {plain, format(n, ",")}

    if n == n.to_integral_value():
        out.add(f"{int(n):,}")

    if metric == "worldscale_assessment":
        out |= {"ws" + x for x in list(out)}

    if metric == "voyage_rate" and n >= Decimal("1000000"):
        millions = n / Decimal("1000000")
        amount = format(millions, ".2f")
        trimmed = format(millions, "f").rstrip("0").rstrip(".")

        out.add(amount + " million")
        out.add(trimmed + " million")
        out.add("$" + amount + "m")
        out.add("$" + trimmed + "m")

    return {normalize(item) for item in out if item}


def token_found(text, value, metric):
    """Check whether a numeric representation appears in the source paragraph.

    This is a token-presence check only. It does not verify meaning or direction.
    """
    source = normalize(text)
    return any(token in source for token in variants(value, metric))


def main():
    for path in (PARAGRAPHS, CANDIDATES, REPORT):
        if not path.exists():
            print(f"FAIL: missing file: {path}")
            return 2

    errors = []
    review_flags = []

    # Load source paragraphs and map each route code to its source paragraph.
    with PARAGRAPHS.open(newline="", encoding="utf-8-sig") as f:
        source_rows = list(csv.DictReader(f))

    source_by_route = {}
    for row in source_rows:
        for code in (row.get("route_codes") or "").split(";"):
            code = code.strip()
            if code:
                source_by_route[code] = row.get("full_paragraph", "")

    # Load candidate data.
    with CANDIDATES.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fields = set(reader.fieldnames or [])
        rows = list(reader)

    missing_columns = sorted(REQUIRED_FIELDS - fields)
    if missing_columns:
        errors.append("Missing columns: " + ", ".join(missing_columns))

    keys = []

    for line, row in enumerate(rows, start=2):
        code = (row.get("route_code") or "").strip()
        metric = (row.get("metric") or "").strip()
        unit = (row.get("unit") or "").strip()
        value_qualifier = (row.get("value_qualifier") or "").strip()
        change_qualifier = (row.get("weekly_change_qualifier") or "").strip()
        change_value = (row.get("weekly_change_value") or "").strip()
        change_unit = (row.get("weekly_change_unit") or "").strip()

        keys.append((code, metric))

        # Required-field checks, excluding optional weekly-change fields.
        for field in REQUIRED_FIELDS - OPTIONAL_CHANGE_FIELDS:
            if not (row.get(field) or "").strip():
                errors.append(f"line {line}: missing {field}")

        # Review-state and provenance checks.
        if row.get("review_status") != REVIEW_STATUS:
            errors.append(f"line {line}: review status changed unexpectedly")

        if row.get("provenance") != "published_source_data":
            errors.append(f"line {line}: unexpected provenance")

        source_url = row.get("source_url") or ""
        if not source_url.startswith("https://www.balticexchange.com/"):
            errors.append(f"line {line}: unexpected source URL")

        # Metric and unit validation.
        if metric not in ALLOWED_UNITS:
            errors.append(f"line {line}: unknown metric {metric!r}")
        elif unit not in ALLOWED_UNITS[metric]:
            errors.append(
                f"line {line}: unexpected unit {unit!r} for metric {metric!r}"
            )

        # Qualifier vocabulary validation.
        if value_qualifier not in ALLOWED_VALUE_QUALIFIERS:
            errors.append(
                f"line {line}: unknown value qualifier {value_qualifier!r}"
            )

        if change_qualifier and change_qualifier not in ALLOWED_CHANGE_QUALIFIERS:
            errors.append(
                f"line {line}: unknown weekly-change qualifier "
                f"{change_qualifier!r}"
            )

        # Current value numeric and source-token checks.
        current_value = row.get("value") or ""
        parsed_value = dec(current_value)

        if parsed_value is None:
            errors.append(
                f"line {line}: nonnumeric current value {current_value!r}"
            )
        elif metric in ALLOWED_UNITS and not token_found(
            row.get("source_text", ""), current_value, metric
        ):
            review_flags.append(
                f"line {line} {code}/{metric}: "
                "current value token not found in source text"
            )

        # Weekly-change consistency and source-token checks.
        if change_value:
            if dec(change_value) is None:
                errors.append(
                    f"line {line}: nonnumeric weekly change {change_value!r}"
                )

            if not change_qualifier:
                errors.append(
                    f"line {line}: weekly change has no qualifier"
                )

            if not change_unit:
                errors.append(
                    f"line {line}: weekly change has no unit"
                )
            elif metric in ALLOWED_UNITS and change_unit not in ALLOWED_UNITS[metric]:
                errors.append(
                    f"line {line}: unexpected weekly-change unit "
                    f"{change_unit!r} for metric {metric!r}"
                )

            if (
                dec(change_value) is not None
                and metric in ALLOWED_UNITS
                and not token_found(row.get("source_text", ""), change_value, metric)
            ):
                review_flags.append(
                    f"line {line} {code}/{metric}: "
                    "weekly-change token not found in source text"
                )
        else:
            # A change unit may be present even when no weekly change is reported.
            # A qualifier, however, must not imply a change value that is absent.
            if change_qualifier:
                errors.append(
                    f"line {line}: change qualifier exists without a change value"
                )

        # Verify that the saved source paragraph matches the extracted paragraph.
        source_para = source_by_route.get(code)

        if source_para is None:
            errors.append(
                f"line {line}: route code {code!r} not mapped "
                "to extracted source paragraph"
            )
        elif normalize(source_para) != normalize(row.get("source_text", "")):
            errors.append(
                f"line {line}: source_text differs from extracted paragraph "
                f"for {code}"
            )

    # Dataset-size and uniqueness checks.
    duplicates = [
        key for key, count in Counter(keys).items() if count > 1
    ]

    if len(rows) != EXPECTED_ROWS:
        errors.append(f"expected {EXPECTED_ROWS} rows, got {len(rows)}")

    routes = {row.get("route_code", "").strip() for row in rows}
    if len(routes) != EXPECTED_ROUTES:
        errors.append(
            f"expected {EXPECTED_ROUTES} routes, got {len(routes)}"
        )

    if duplicates:
        errors.append(f"duplicate route/metric pairs: {duplicates}")

    # Report safeguards.
    try:
        report = json.loads(REPORT.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        errors.append(f"could not read valid report JSON: {exc}")
        report = {}

    if report.get("supabase_writes") is not False:
        errors.append("report must retain supabase_writes=false")

    if report.get("mode") != "LOCAL_NORMALIZATION_ONLY":
        errors.append("report must retain LOCAL_NORMALIZATION_ONLY")

    if report.get("review_status") != REVIEW_STATUS:
        errors.append("report must retain review-required status")

    # Summary.
    print(f"Rows: {len(rows)}")
    print(f"Unique routes: {len(routes)}")
    print(f"Duplicate route/metric pairs: {len(duplicates)}")
    print(f"Errors: {len(errors)}")
    print(f"Numeric token review flags: {len(review_flags)}")

    for error in errors[:50]:
        print("ERROR:", error)

    for flag in review_flags[:50]:
        print("REVIEW:", flag)

    if errors:
        print("FAIL: correct errors before downstream use.")
        return 1

    print(
        "PASS: structural and source-token checks passed. "
        "Numeric token matching is not full semantic verification."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
