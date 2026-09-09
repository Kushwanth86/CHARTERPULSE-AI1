from pathlib import Path
import csv
from collections import Counter

ROOT = Path("data/raw/unlocode/release/release/csv")

FILES = [
    ROOT / "UNLOCODE CodeListPart1.csv",
    ROOT / "UNLOCODE CodeListPart2.csv",
    ROOT / "UNLOCODE CodeListPart3.csv",
]

FIELD_COUNT = 12

locodes = []
malformed = []
country_headers = 0
data_rows = 0

for path in FILES:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)

        for line_number, row in enumerate(reader, start=1):
            if not row or all(not value.strip() for value in row):
                continue

            if len(row) != FIELD_COUNT:
                malformed.append(
                    {
                        "file": path.name,
                        "line": line_number,
                        "field_count": len(row),
                        "raw": row,
                    }
                )
                continue

            country = row[1].strip()
            location = row[2].strip()
            name = row[3].strip()

            if country and not location and name.startswith("."):
                country_headers += 1
                continue

            if len(country) == 2 and len(location) == 3:
                data_rows += 1
                locodes.append(f"{country}{location}")

counts = Counter(locodes)
duplicates = {
    locode: count
    for locode, count in counts.items()
    if count > 1
}

print()
print("========== RAW UNECE VALIDATION ==========")
print(f"Country header rows : {country_headers:,}")
print(f"Location rows       : {data_rows:,}")
print(f"Unique LOCODEs      : {len(counts):,}")
print(f"Duplicate LOCODEs   : {len(duplicates):,}")
print(f"Duplicate rows      : {sum(count - 1 for count in duplicates.values()):,}")
print(f"Malformed rows      : {len(malformed):,}")

if duplicates:
    print()
    print("========== DUPLICATE LOCODES ==========")
    for locode, count in sorted(
        duplicates.items(),
        key=lambda x: (-x[1], x[0])
    )[:50]:
        print(f"{locode}: {count}")

if malformed:
    print()
    print("========== MALFORMED ROWS ==========")
    for item in malformed[:50]:
        print(
            f"{item['file']}:{item['line']} "
            f"fields={item['field_count']} "
            f"{item['raw']}"
        )

print()
print("========== EXPECTED PROCESSED DATA ==========")
print(f"Processed locations: 116,086")
print(f"Processed unique LOCODEs: 116,086")
print(
    "Processed counts match raw unique count:"
    f" {len(counts) == 116086}"
)
