from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "unlocode"
    / "unlocode_2025_1_normalized.jsonl"
)


def main() -> int:
    if not INPUT.exists():
        print(f"Missing normalized dataset: {INPUT}")
        return 2

    records = []

    with INPUT.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()

            if line:
                records.append(json.loads(line))

    keys = set()
    duplicate_keys = []
    invalid_keys = []

    for record in records:
        key = (
            record.get("country"),
            record.get("location"),
        )

        if not record.get("country") or len(record["country"]) != 2:
            invalid_keys.append(key)

        if not record.get("location") or len(record["location"]) != 3:
            invalid_keys.append(key)

        if key in keys:
            duplicate_keys.append(key)

        keys.add(key)

    print("========== UN/LOCODE VALIDATION ==========")
    print(f"Records          : {len(records)}")
    print(f"Unique codes     : {len(keys)}")
    print(f"Duplicate codes  : {len(duplicate_keys)}")
    print(f"Invalid codes    : {len(invalid_keys)}")

    if duplicate_keys:
        print("\nFirst duplicate keys:")
        for key in duplicate_keys[:20]:
            print(" ", key)

    if invalid_keys:
        print("\nFirst invalid keys:")
        for key in invalid_keys[:20]:
            print(" ", key)

    return 1 if duplicate_keys or invalid_keys else 0


if __name__ == "__main__":
    raise SystemExit(main())
