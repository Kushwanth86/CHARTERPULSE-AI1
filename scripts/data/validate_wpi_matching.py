from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from services.api.app.repositories.supabase_client import get_supabase_client


ROOT = Path(__file__).resolve().parents[2]
WPI_FILE = ROOT / "data" / "processed" / "wpi" / "wpi_normalized.jsonl"
REPORT_FILE = ROOT / "data" / "processed" / "wpi" / "wpi_matching_report.json"

UNLOCODE_PATTERN = re.compile(r"^[A-Z]{2}[A-Z0-9]{3}$")
PAGE_SIZE = 1000


def load_wpi_records() -> list[dict]:
    if not WPI_FILE.exists():
        raise FileNotFoundError(f"WPI normalized file not found: {WPI_FILE}")

    records = []

    with WPI_FILE.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    f"Invalid JSON on line {line_number}: {exc}"
                ) from exc

            records.append(record)

    return records


def is_valid_unlocode(value: object) -> bool:
    return bool(
        isinstance(value, str)
        and UNLOCODE_PATTERN.fullmatch(value)
    )


def fetch_column(table_name: str, column: str) -> list[dict]:
    client = get_supabase_client()
    rows: list[dict] = []
    offset = 0

    while True:
        response = (
            client
            .table(table_name)
            .select(column)
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
        )

        batch = response.data or []

        if not batch:
            break

        rows.extend(batch)

        if len(batch) < PAGE_SIZE:
            break

        offset += PAGE_SIZE

    return rows


def build_report(records: list[dict]) -> dict:
    missing = []
    invalid = []
    valid = []

    for record in records:
        unlocode = record.get("unlocode")

        if not unlocode:
            missing.append(record)
        elif not is_valid_unlocode(unlocode):
            invalid.append(record)
        else:
            valid.append(record)

    counts = Counter(
        record["unlocode"]
        for record in valid
    )

    duplicate_unlocodes = sorted(
        value
        for value, count in counts.items()
        if count > 1
    )

    unique_valid_unlocodes = sorted(
        value
        for value, count in counts.items()
        if count == 1
    )

    location_rows = fetch_column("locations", "unlocode")
    port_rows = fetch_column("ports", "unlocode")

    location_unlocodes = {
        row["unlocode"].strip().upper()
        for row in location_rows
        if row.get("unlocode")
    }

    port_unlocodes = {
        row["unlocode"].strip().upper()
        for row in port_rows
        if row.get("unlocode")
    }

    unique_valid_set = set(unique_valid_unlocodes)

    matched_locations = sorted(
        unique_valid_set & location_unlocodes
    )

    matched_ports = sorted(
        unique_valid_set & port_unlocodes
    )

    unmatched_locations = sorted(
        unique_valid_set - location_unlocodes
    )

    unmatched_ports = sorted(
        unique_valid_set - port_unlocodes
    )

    return {
        "source": "NGA World Port Index",
        "wpi_record_count": len(records),
        "missing_unlocode": len(missing),
        "invalid_unlocode": len(invalid),
        "valid_unlocode_records": len(valid),
        "valid_unique_unlocodes": len(unique_valid_unlocodes),
        "duplicate_valid_unlocodes": len(duplicate_unlocodes),
        "duplicate_unlocode_values": duplicate_unlocodes,
        "locations_unlocode_count": len(location_unlocodes),
        "ports_unlocode_count": len(port_unlocodes),
        "wpi_unique_matched_to_locations": len(matched_locations),
        "wpi_unique_unmatched_to_locations": len(unmatched_locations),
        "wpi_unique_matched_to_ports": len(matched_ports),
        "wpi_unique_unmatched_to_ports": len(unmatched_ports),
        "matched_location_unlocodes": matched_locations,
        "matched_port_unlocodes": matched_ports,
        "unmatched_location_unlocodes": unmatched_locations,
        "unmatched_port_unlocodes": unmatched_ports,
    }


def main() -> int:
    print("WPI IDENTIFIER VALIDATION / MATCHING")
    print("Mode: READ-ONLY")
    print(f"WPI input: {WPI_FILE}")

    records = load_wpi_records()

    print(f"WPI records loaded: {len(records)}")

    report = build_report(records)

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)

    REPORT_FILE.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print()
    print(f"WPI records: {report['wpi_record_count']}")
    print(f"Missing UN/LOCODE: {report['missing_unlocode']}")
    print(f"Invalid UN/LOCODE: {report['invalid_unlocode']}")
    print(f"Valid UN/LOCODE records: {report['valid_unlocode_records']}")
    print(f"Valid unique UN/LOCODEs: {report['valid_unique_unlocodes']}")
    print(
        "Duplicate valid UN/LOCODEs: "
        f"{report['duplicate_valid_unlocodes']}"
    )
    print()
    print(
        "WPI unique matched to locations: "
        f"{report['wpi_unique_matched_to_locations']}"
    )
    print(
        "WPI unique unmatched to locations: "
        f"{report['wpi_unique_unmatched_to_locations']}"
    )
    print(
        "WPI unique matched to ports: "
        f"{report['wpi_unique_matched_to_ports']}"
    )
    print(
        "WPI unique unmatched to ports: "
        f"{report['wpi_unique_unmatched_to_ports']}"
    )
    print()
    print(f"Report: {REPORT_FILE}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
