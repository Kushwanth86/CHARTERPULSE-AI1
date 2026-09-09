from pathlib import Path
import csv
from collections import defaultdict

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

            if len(country) == 2 and len(location) == 3:
                locode = country + location

                records[locode].append({
                    "file": path.name,
                    "line": line_number,
                    "change": row[0].strip(),
                    "country": country,
                    "location": location,
                    "name": row[3].strip(),
                    "name_wo_diacritics": row[4].strip(),
                    "subdiv": row[5].strip(),
                    "function": row[6].strip(),
                    "status": row[7].strip(),
                    "date": row[8].strip(),
                    "iata": row[9].strip(),
                    "coordinates": row[10].strip(),
                    "remarks": row[11].strip(),
                })

duplicates = {
    locode: rows
    for locode, rows in records.items()
    if len(rows) > 1
}

print()
print("========== DUPLICATE SOURCE RECORDS ==========")
print(f"Duplicate LOCODE groups: {len(duplicates):,}")
print(
    f"Duplicate source rows: "
    f"{sum(len(rows) - 1 for rows in duplicates.values()):,}"
)

for locode in sorted(duplicates):
    print()
    print(f"LOCODE: {locode}")
    print("-" * 100)

    for row in duplicates[locode]:
        print(
            f"{row['file']}:{row['line']} | "
            f"change={row['change']!r} | "
            f"name={row['name']!r} | "
            f"subdiv={row['subdiv']!r} | "
            f"function={row['function']!r} | "
            f"status={row['status']!r} | "
            f"date={row['date']!r} | "
            f"IATA={row['iata']!r} | "
            f"coords={row['coordinates']!r} | "
            f"remarks={row['remarks']!r}"
        )
