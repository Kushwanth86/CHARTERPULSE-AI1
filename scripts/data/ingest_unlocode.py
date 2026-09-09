from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

CSV_ROOT = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "unlocode"
    / "release"
    / "release"
    / "csv"
)

OUTPUT_ROOT = PROJECT_ROOT / "data" / "processed" / "unlocode"
QUALITY_ROOT = PROJECT_ROOT / "data" / "quality"

SOURCE = "UNECE UN/LOCODE"
SOURCE_VERSION = "2025-1"
PROVENANCE = "REAL"

PART_FILES = [
    "UNLOCODE CodeListPart1.csv",
    "UNLOCODE CodeListPart2.csv",
    "UNLOCODE CodeListPart3.csv",
]

FIELDS = [
    "change",
    "country",
    "location",
    "name",
    "name_wo_diacritics",
    "subdiv",
    "function",
    "status",
    "date",
    "iata",
    "coordinates",
    "remarks",
]

COORDINATE_PATTERN = re.compile(
    r"^\s*(\d{2})(\d{2})([NS])\s+"
    r"(\d{3})(\d{2})([EW])\s*$"
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean(value: str | None) -> str:
    return "" if value is None else value.strip()


def optional(value: str | None) -> str | None:
    value = clean(value)
    return value if value else None


def parse_coordinates(value: str | None):
    value = clean(value)

    if not value:
        return None, None, "MISSING"

    match = COORDINATE_PATTERN.match(value)

    if not match:
        return None, None, "INVALID"

    lat_deg, lat_min, lat_dir, lon_deg, lon_min, lon_dir = match.groups()

    latitude = int(lat_deg) + int(lat_min) / 60
    longitude = int(lon_deg) + int(lon_min) / 60

    if lat_dir == "S":
        latitude = -latitude

    if lon_dir == "W":
        longitude = -longitude

    if not -90 <= latitude <= 90:
        return None, None, "INVALID"

    if not -180 <= longitude <= 180:
        return None, None, "INVALID"

    return round(latitude, 6), round(longitude, 6), "VALID"


def record_hash(row: dict[str, str]) -> str:
    payload = json.dumps(
        row,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(payload).hexdigest()


def read_source_rows():
    for filename in PART_FILES:
        path = CSV_ROOT / filename

        if not path.exists():
            raise FileNotFoundError(path)

        with path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as handle:
            reader = csv.reader(handle)

            for line_number, values in enumerate(reader, start=1):

                if not values or all(not clean(v) for v in values):
                    continue

                if len(values) != 12:
                    yield {
                        "type": "MALFORMED",
                        "file": filename,
                        "line": line_number,
                        "raw": values,
                    }
                    continue

                row = dict(zip(FIELDS, values))

                country = clean(row["country"])
                location = clean(row["location"])
                name = clean(row["name"])

                if (
                    country
                    and not location
                    and name.startswith(".")
                ):
                    yield {
                        "type": "COUNTRY",
                        "file": filename,
                        "line": line_number,
                        "row": row,
                    }
                    continue

                if len(country) == 2 and len(location) == 3:
                    yield {
                        "type": "LOCATION",
                        "file": filename,
                        "line": line_number,
                        "row": row,
                    }
                    continue

                yield {
                    "type": "MALFORMED",
                    "file": filename,
                    "line": line_number,
                    "raw": values,
                }


def main():
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    QUALITY_ROOT.mkdir(parents=True, exist_ok=True)

    observed_at = now_utc()

    source_records = []
    countries = []
    malformed = []

    by_locode = defaultdict(list)

    coordinate_counts = {
        "VALID": 0,
        "MISSING": 0,
        "INVALID": 0,
    }

    country_seen = set()

    for item in read_source_rows():

        if item["type"] == "MALFORMED":
            malformed.append(item)
            continue

        if item["type"] == "COUNTRY":
            row = item["row"]

            country = clean(row["country"])
            name = clean(row["name"]).lstrip(".").strip()

            if country not in country_seen:
                countries.append(
                    {
                        "country": country,
                        "name": name,
                        "source": SOURCE,
                        "source_version": SOURCE_VERSION,
                        "provenance": PROVENANCE,
                        "source_file": item["file"],
                        "source_line": item["line"],
                        "observed_at": observed_at,
                    }
                )

                country_seen.add(country)

            continue

        row = item["row"]

        country = clean(row["country"])
        location = clean(row["location"])
        locode = country + location

        latitude, longitude, coordinate_quality = parse_coordinates(
            row["coordinates"]
        )

        coordinate_counts[coordinate_quality] += 1

        record = {
            "source_record_id": record_hash(row),
            "locode": locode,
            "country": country,
            "location": location,
            "name": clean(row["name"]),
            "name_wo_diacritics": clean(row["name_wo_diacritics"]),
            "subdivision": optional(row["subdiv"]),
            "function": clean(row["function"]),
            "status": clean(row["status"]),
            "change": optional(row["change"]),
            "date": optional(row["date"]),
            "iata": optional(row["iata"]),
            "coordinates_raw": optional(row["coordinates"]),
            "latitude": latitude,
            "longitude": longitude,
            "coordinate_quality": coordinate_quality,
            "remarks": optional(row["remarks"]),
            "source": SOURCE,
            "source_version": SOURCE_VERSION,
            "provenance": PROVENANCE,
            "source_file": item["file"],
            "source_line": item["line"],
            "observed_at": observed_at,
        }

        source_records.append(record)
        by_locode[locode].append(record)

    # Canonical record selection.
    #
    # UNECE change markers are preserved, but we do not interpret them
    # as business truth beyond selecting the most recent dated record.
    #
    # Selection priority:
    # 1. highest YYYYMM date
    # 2. record with a non-empty change marker
    # 3. source file / line as deterministic tie-breaker
    #
    # ALL source records remain preserved separately.
    canonical = []
    duplicate_relationships = []

    for locode, records in by_locode.items():

        def sort_key(record):
            date_value = record["date"] or "0000"

            return (
                date_value,
                1 if record["change"] else 0,
                record["source_file"],
                record["source_line"],
            )

        ordered = sorted(records, key=sort_key, reverse=True)

        selected = dict(ordered[0])
        selected["canonical"] = True
        selected["source_record_count"] = len(records)

        canonical.append(selected)

        for record in ordered[1:]:
            duplicate_relationships.append(
                {
                    "locode": locode,
                    "canonical_source_record_id": selected[
                        "source_record_id"
                    ],
                    "related_source_record_id": record[
                        "source_record_id"
                    ],
                    "relationship": "SAME_LOCODE_SOURCE_HISTORY",
                    "source_version": SOURCE_VERSION,
                    "source": SOURCE,
                    "observed_at": observed_at,
                }
            )

    canonical.sort(key=lambda x: x["locode"])
    countries.sort(key=lambda x: x["country"])
    source_records.sort(
        key=lambda x: (
            x["locode"],
            x["date"] or "",
            x["source_file"],
            x["source_line"],
        )
    )
    duplicate_relationships.sort(
        key=lambda x: (
            x["locode"],
            x["related_source_record_id"],
        )
    )

    source_path = OUTPUT_ROOT / "unlocode_source_records.jsonl"
    canonical_path = OUTPUT_ROOT / "unlocode_canonical.jsonl"
    duplicate_path = OUTPUT_ROOT / "unlocode_duplicates.jsonl"
    country_path = OUTPUT_ROOT / "countries.jsonl"
    malformed_path = OUTPUT_ROOT / "unlocode_malformed.jsonl"
    quality_path = QUALITY_ROOT / "unlocode_2025-1_quality.json"

    def write_jsonl(path, records):
        with path.open(
            "w",
            encoding="utf-8",
            newline="\n",
        ) as handle:
            for record in records:
                handle.write(
                    json.dumps(
                        record,
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )
                    + "\n"
                )

    write_jsonl(source_path, source_records)
    write_jsonl(canonical_path, canonical)
    write_jsonl(duplicate_path, duplicate_relationships)
    write_jsonl(country_path, countries)
    write_jsonl(malformed_path, malformed)

    duplicate_groups = sum(
        1
        for records in by_locode.values()
        if len(records) > 1
    )

    duplicate_extra_rows = sum(
        len(records) - 1
        for records in by_locode.values()
        if len(records) > 1
    )

    quality = {
        "source": SOURCE,
        "source_version": SOURCE_VERSION,
        "provenance": PROVENANCE,
        "observed_at": observed_at,
        "country_count": len(countries),
        "raw_location_rows": len(source_records),
        "canonical_locodes": len(canonical),
        "duplicate_locode_groups": duplicate_groups,
        "duplicate_extra_rows": duplicate_extra_rows,
        "malformed_rows": len(malformed),
        "coordinate_quality": coordinate_counts,
        "outputs": {
            "source_records": str(
                source_path.relative_to(PROJECT_ROOT)
            ),
            "canonical": str(
                canonical_path.relative_to(PROJECT_ROOT)
            ),
            "duplicates": str(
                duplicate_path.relative_to(PROJECT_ROOT)
            ),
            "countries": str(
                country_path.relative_to(PROJECT_ROOT)
            ),
            "malformed": str(
                malformed_path.relative_to(PROJECT_ROOT)
            ),
        },
    }

    quality_path.write_text(
        json.dumps(
            quality,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print()
    print("========== UNECE UN/LOCODE INGESTION ==========")
    print(f"Source                 : {SOURCE}")
    print(f"Version                : {SOURCE_VERSION}")
    print(f"Countries              : {len(countries):,}")
    print(f"Raw location rows      : {len(source_records):,}")
    print(f"Canonical LOCODEs      : {len(canonical):,}")
    print(f"Duplicate groups       : {duplicate_groups:,}")
    print(f"Duplicate extra rows   : {duplicate_extra_rows:,}")
    print(f"Malformed rows         : {len(malformed):,}")
    print()
    print("Coordinate quality:")
    for key, value in coordinate_counts.items():
        print(f"  {key:8}: {value:,}")

    print()
    print("Outputs:")
    print(f"  Source records : {source_path}")
    print(f"  Canonical     : {canonical_path}")
    print(f"  Duplicates    : {duplicate_path}")
    print(f"  Countries     : {country_path}")
    print(f"  Malformed     : {malformed_path}")
    print(f"  Quality       : {quality_path}")


if __name__ == "__main__":
    main()
