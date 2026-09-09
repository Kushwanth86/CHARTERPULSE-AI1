from pathlib import Path
import csv
from collections import Counter, defaultdict

ROOT = Path("data/raw/unlocode/release/release/csv")

FILES = [
    ROOT / "UNLOCODE CodeListPart1.csv",
    ROOT / "UNLOCODE CodeListPart2.csv",
    ROOT / "UNLOCODE CodeListPart3.csv",
]

records = defaultdict(list)

for path in FILES:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)

        for line_number, row in enumerate(reader, start=1):
            if len(row) != 12:
                continue

            country = row[1].strip()
            location = row[2].strip()

            if len(country) != 2 or len(location) != 3:
                continue

            records[country + location].append({
                "file": path.name,
                "line": line_number,
                "change": row[0].strip(),
                "name": row[3].strip(),
                "subdiv": row[5].strip(),
                "function": row[6].strip(),
                "status": row[7].strip(),
                "date": row[8].strip(),
                "coordinates": row[10].strip(),
                "remarks": row[11].strip(),
            })

duplicates = {
    locode: rows
    for locode, rows in records.items()
    if len(rows) > 1
}

change_counts = Counter()
duplicate_group_patterns = Counter()

for locode, rows in duplicates.items():
    changes = tuple(sorted(row["change"] or "<blank>" for row in rows))

    for row in rows:
        change_counts[row["change"] or "<blank>"] += 1

    duplicate_group_patterns[changes] += 1

print()
print("========== DUPLICATE CHANGE-CODE ANALYSIS ==========")
print(f"Duplicate LOCODE groups : {len(duplicates):,}")
print(
    "Duplicate source rows   : "
    f"{sum(len(rows) - 1 for rows in duplicates.values()):,}"
)

print()
print("========== CHANGE CODES IN DUPLICATE RECORDS ==========")

for change, count in change_counts.most_common():
    print(f"{change!r:12} {count:,}")

print()
print("========== DUPLICATE GROUP PATTERNS ==========")

for pattern, count in duplicate_group_patterns.most_common(30):
    print(f"{count:5,}  {pattern}")

print()
print("========== ALL DUPLICATE LOCODES BY CHANGE PATTERN ==========")

for locode in sorted(duplicates):
    rows = duplicates[locode]

    pattern = tuple(sorted(row["change"] or "<blank>" for row in rows))

    print(
        f"{locode:5}  {pattern}  "
        + " | ".join(
            f"{row['date'] or '-'}:{row['change'] or '-'}:{row['name']}"
            for row in rows
        )
    )
