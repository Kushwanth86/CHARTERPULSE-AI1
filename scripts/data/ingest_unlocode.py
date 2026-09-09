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


def classify_row(row: dict[str, str]) -> str:
    """
    UNECE UN/LOCODE contains both current location records and
    source-history/change records.

    A row is not malformed merely because its location field is blank.

    Supported source row types:
      COUNTRY
      LOCATION
      HISTORY
    """

    country = clean(row["country"])
    location = clean(row["location"])
    name = clean(row["name"])
    change = clean(row["change"])

    # Country header:
    # ,AD,,.ANDORRA,,,,,,,,
    if (
        country
        and not location
        and name.startswith(".")
    ):
        return "COUNTRY"

    # Normal location:
    # ,AD,ALV,Andorra la Vella,...
    if len(country) == 2 and len(location) == 3:
        return "LOCATION"

    # UNECE source-history/change rows can have a blank location.
    # Examples include change code "=" with an existing country/name.
    #
    # These rows have a valid 12-column UNECE structure and must be
    # preserved as source history, not labelled malformed.
    if (
        len(country) == 2
        and not location
        and (
            change
            or name
            or clean(row["name_wo_diacritics"])
            or clean(row["subdiv"])
            or clean(row["function"])
            or clean(row["status"])
            or clean(row["date"])
            or clean(row["iata"])
            or clean(row["coordinates"])
            or clean(row["remarks"])
        )
    ):
        return "HISTORY"

    return "MALFORMED"


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
                        "reason": "EXPECTED_12_FIELDS",
                    }
                    continue

                row = {
                    field: clean(value)
                    for field, value in zip(FIELDS, values)
                }

                row_type = classify_row(row)

                yield {
                    "type": row_type,
                    "file": filename,
                    "line": line_number,
                    "row": row,
                }


def build_source_record(
    row: dict[str, str],
    row_type: str,
    filename: str,
    line_number: int,
    observed_at: str,
):
    country = clean(row["country"])
    location = clean(row["location"])

    locode = None

    if len(country) == 2 and len(location) == 3:
        locode = f"{country}{location}".upper()

    latitude, longitude, coordinate_quality = parse_coordinates(
        row["coordinates"]
    )

    source_record_id = hashlib.sha256(
        (
            f"{SOURCE}|{SOURCE_VERSION}|"
            f"{filename}|{line_number}|"
            f"{record_hash(row)}"
        ).encode("utf-8")
    ).hexdigest()

    return {
        "source_record_id": source_record_id,
        "record_type": row_type,
        "locode": locode,
        "change": optional(row["change"]),
        "country": optional(row["country"]),
        "location": optional(row["location"]),
        "name": optional(row["name"]),
        "name_wo_diacritics": optional(row["name_wo_diacritics"]),
        "subdiv": optional(row["subdiv"]),
        "function": optional(row["function"]),
        "status": optional(row["status"]),
        "date": optional(row["date"]),
        "iata": optional(row["iata"]),
        "coordinates": optional(row["coordinates"]),
        "latitude": latitude,
        "longitude": longitude,
        "coordinate_quality": coordinate_quality,
        "remarks": optional(row["remarks"]),
        "source": SOURCE,
        "source_version": SOURCE_VERSION,
        "provenance": PROVENANCE,
        "source_file": filename,
        "source_line": line_number,
        "observed_at": observed_at,
    }


def canonical_sort_key(record):
    """
    Deterministic canonical selection.

    This is an ingestion-layer selection rule, NOT an assertion that
    UNECE defines canonical identity using this exact ordering.

    Preference:
      1. Latest source date
      2. Non-empty change code
      3. Current location record over history
      4. Deterministic file/line ordering
    """

    return (
        record["date"] or "",
        1 if record["change"] else 0,
        1 if record["record_type"] == "LOCATION" else 0,
        record["source_file"],
        record["source_line"],
    )


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

    record_type_counts = {
        "COUNTRY": 0,
        "LOCATION": 0,
        "HISTORY": 0,
        "MALFORMED": 0,
    }

    country_seen = set()

    for item in read_source_rows():

        record_type = item["type"]
        record_type_counts[record_type] += 1

        if record_type == "MALFORMED":
            malformed.append(item)
            continue

        if record_type == "COUNTRY":
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

        source_record = build_source_record(
            row=row,
            row_type=record_type,
            filename=item["file"],
            line_number=item["line"],
            observed_at=observed_at,
        )

        source_records.append(source_record)

        coordinate_counts[
            source_record["coordinate_quality"]
        ] += 1

        locode = source_record["locode"]

        # Only actual LOCODE-bearing records participate in canonical
        # identity selection.
        if locode:
            by_locode[locode].append(source_record)

    canonical = []
    duplicate_relationships = []

    for locode, records in by_locode.items():

        selected = sorted(
            records,
            key=canonical_sort_key,
            reverse=True,
        )[0]

        canonical.append(selected)

        for record in records:
            if record["source_record_id"] == selected["source_record_id"]:
                continue

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

    canonical.sort(
        key=lambda x: x["locode"] or ""
    )

    countries.sort(
        key=lambda x: x["country"]
    )

    source_records.sort(
        key=lambda x: (
            x["locode"] or "",
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
        "raw_source_records": len(source_records),
        "location_records": record_type_counts["LOCATION"],
        "history_records": record_type_counts["HISTORY"],
        "canonical_locodes": len(canonical),
        "duplicate_locode_groups": duplicate_groups,
        "duplicate_extra_rows": duplicate_extra_rows,
        "malformed_rows": len(malformed),
        "record_type_counts": record_type_counts,
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
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print("========== UNECE UN/LOCODE INGESTION ==========")
    print(f"Source                 : {SOURCE}")
    print(f"Version                : {SOURCE_VERSION}")
    print(f"Countries              : {len(countries):,}")
    print(f"Raw source records     : {len(source_records):,}")
    print(f"Location records       : {record_type_counts['LOCATION']:,}")
    print(f"History records        : {record_type_counts['HISTORY']:,}")
    print(f"Canonical LOCODEs      : {len(canonical):,}")
    print(f"Duplicate groups       : {duplicate_groups:,}")
    print(f"Duplicate extra rows   : {duplicate_extra_rows:,}")
    print(f"Malformed rows         : {len(malformed):,}")
    print()
    print("Coordinate quality:")
    for key, value in coordinate_counts.items():
        print(f"  {key:8}: {value:,}")

    print()
    print("Record types:")
    for key, value in record_type_counts.items():
        print(f"  {key:10}: {value:,}")

    print()
    print("Outputs:")
    print(f"  Source records : {source_path}")
    print(f"  Canonical      : {canonical_path}")
    print(f"  Duplicates     : {duplicate_path}")
    print(f"  Countries      : {country_path}")
    print(f"  Malformed      : {malformed_path}")
    print(f"  Quality        : {quality_path}")


if __name__ == "__main__":
    main()
