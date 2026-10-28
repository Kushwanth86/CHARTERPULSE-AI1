
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
    for token in variants(value, metric):
        # Numeric candidates must match whole numeric/text tokens. Plain substring
        # matching incorrectly lets 12 match 312 or 12.5, and 1075 match 10750.
        pattern = rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])(?![.,]\d)"
        if re.search(pattern, source):
            return True
    return False


def route_context(text, route_code):
    """Return a route's source span, including following metric sentences.

    Weekly reports may state an index in one sentence and the TCE in the next.
    This context starts at the route-code mention and ends before the next
    different route-code mention. A missing route returns an empty string.
    """
    text = text or ""
    route_code = (route_code or "").strip().upper()
    if not route_code:
        return ""

    # Baltic tanker route identifiers such as TC1, TC20, and TD3C.
    route_pattern = re.compile(
        r"(?<![A-Z0-9])((?:TC|TD)\d{1,3}[A-Z]?)(?![A-Z0-9])",
        re.IGNORECASE,
    )
    matches = list(route_pattern.finditer(text))
    target = next(
        (match for match in matches if match.group(1).upper() == route_code),
        None,
    )
    if target is None:
        return ""

    end = len(text)
    for match in matches:
        if match.start() > target.start() and match.group(1).upper() != route_code:
            end = match.start()
            break
    return text[target.start():end].strip()


DIRECTION_CUES = {
    "up": re.compile(r"\b(?:rose|rise|risen|rising|climbed|climb|climbs|climbing|gained|gain|gains|gaining|jumped|jump|increased|increase|increases|increasing|added|up|higher|strengthened|firmed)\b", re.I),
    "down": re.compile(r"\b(?:fell|fall|fallen|falling|dropped|drop|drops|dropping|slipped|slip|slips|slipping|tumbled|tumble|eased|ease|eases|easing|declined|decline|decreased|decrease|down|lower|weaker|weakened)\b", re.I),
}
APPROX_CUES = {
    "about": re.compile(r"\b(?:about|around|approximately|approx|roughly)\b", re.I),
    "almost": re.compile(r"\balmost\b", re.I),
    "just_under": re.compile(r"\bjust under\b", re.I),
    "just_over": re.compile(r"\bjust over\b", re.I),
    "over": re.compile(r"\b(?:over|more than|above)\b", re.I),
    "under": re.compile(r"\b(?:under|below|less than)\b", re.I),
    "rounded": re.compile(r"(?:\brounded\b|\$?\d+(?:\.\d+)?\s*(?:m|million|bn|billion)\b)", re.I),
}


def _matching_spans(text, value, metric):
    source = normalize(text)
    spans = []
    for token in sorted(variants(value, metric), key=len, reverse=True):
        pattern = rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])(?![.,]\d)"
        spans.extend((m.start(), m.end()) for m in re.finditer(pattern, source))
    return sorted(set(spans))


def source_direction(text, value, metric):
    """Return up/down only when a nearby directional cue supports it; else None."""
    source = normalize(text)
    spans = _matching_spans(source, value, metric)
    results = set()
    for start, end in spans:
        left = max(0, start - 85)
        window = source[left:min(len(source), end + 25)]
        candidates = [(m.start(), "up") for m in DIRECTION_CUES["up"].finditer(window)]
        candidates += [(m.start(), "down") for m in DIRECTION_CUES["down"].finditer(window)]
        if not candidates:
            continue
        cue_pos, direction = min(candidates, key=lambda item: abs(item[0] - (start - left)))
        if abs(cue_pos - (start - left)) <= 75:
            results.add(direction)
    return next(iter(results)) if len(results) == 1 else None


def qualifier_supported(text, value, metric, qualifier):
    """Return True/False/None for supported, contradicted, or ambiguous qualifier."""
    if not qualifier:
        return None
    source = normalize(text)
    spans = _matching_spans(source, value, metric)
    if not spans:
        return None
    cues = set()
    for start, end in spans:
        window = source[max(0, start - 35):min(len(source), end + 18)]
        for name, pattern in APPROX_CUES.items():
            if pattern.search(window):
                cues.add(name)
    if qualifier == "exact":
        return not bool(cues & {"about", "almost", "just_under", "just_over", "over", "under"})
    if qualifier == "approximate":
        return True if cues & {"about", "rounded"} else None
    if qualifier == "about":
        return "about" in cues
    if qualifier in {"almost", "just_under", "just_over", "over", "under"}:
        return qualifier in cues
    if qualifier == "rounded":
        return "rounded" in cues
    return None


def supported_route_code(route_code):
    """Current Baltic route-code contract; unknown formats must be reviewed."""
    return bool(re.fullmatch(r"(?:TC|TD)\d{1,3}[A-Z]?", (route_code or "").strip().upper()))

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
        route_text = route_context(row.get("source_text", ""), code)

        if not supported_route_code(code):
            review_flags.append(
                f"line {line} {code}: unsupported route-code format; manual review required"
            )

        if parsed_value is None:
            errors.append(
                f"line {line}: nonnumeric current value {current_value!r}"
            )
        elif metric in ALLOWED_UNITS and (
            not route_text or not token_found(route_text, current_value, metric)
        ):
            review_flags.append(
                f"line {line} {code}/{metric}: "
                "current value token not found in route-specific source sentence"
            )

        if parsed_value is not None and route_text:
            qualifier_result = qualifier_supported(route_text, current_value, metric, value_qualifier)
            if qualifier_result is False:
                review_flags.append(
                    f"line {line} {code}/{metric}: value qualifier "
                    f"{value_qualifier!r} conflicts with nearby source wording"
                )
            elif qualifier_result is None and value_qualifier != "exact":
                review_flags.append(
                    f"line {line} {code}/{metric}: value qualifier "
                    f"{value_qualifier!r} could not be semantically verified"
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
                and (
                    not route_text
                    or not token_found(route_text, change_value, metric)
                )
            ):
                review_flags.append(
                    f"line {line} {code}/{metric}: "
                    "weekly-change token not found in route-specific source sentence"
                )

            parsed_change = dec(change_value)
            if parsed_change is not None and parsed_change != 0 and route_text:
                detected_direction = source_direction(route_text, change_value, metric)
                expected_direction = "up" if parsed_change > 0 else "down"
                if detected_direction and detected_direction != expected_direction:
                    errors.append(
                        f"line {line} {code}/{metric}: weekly-change sign "
                        f"{expected_direction!r} conflicts with source direction "
                        f"{detected_direction!r}"
                    )
                elif detected_direction is None:
                    review_flags.append(
                        f"line {line} {code}/{metric}: weekly-change direction "
                        "could not be bound confidently to the numeric token"
                    )

            if parsed_change is not None and route_text:
                change_qualifier_result = qualifier_supported(
                    route_text, change_value, metric, change_qualifier
                )
                if change_qualifier_result is False:
                    review_flags.append(
                        f"line {line} {code}/{metric}: weekly-change qualifier "
                        f"{change_qualifier!r} conflicts with nearby source wording"
                    )
                elif change_qualifier_result is None:
                    review_flags.append(
                        f"line {line} {code}/{metric}: weekly-change qualifier "
                        f"{change_qualifier!r} could not be semantically verified"
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
    print(f"Semantic/source review flags: {len(review_flags)}")

    for error in errors[:50]:
        print("ERROR:", error)

    for flag in review_flags[:50]:
        print("REVIEW:", flag)

    if errors:
        print("FAIL: correct errors before downstream use.")
        return 1

    print(
        "PASS: structural checks passed. Review flags must be resolved before "
        "downstream use; token matching is not full semantic verification."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
