import json
from pathlib import Path

base = Path("data/processed/unlocode")

files = [
    "countries.jsonl",
    "locations.jsonl",
    "unlocode_canonical.jsonl",
    "unlocode_duplicates.jsonl",
]

for filename in files:
    path = base / filename

    print()
    print("=" * 72)
    print(filename)
    print("=" * 72)

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                record = json.loads(line)
                print(json.dumps(
                    record,
                    indent=2,
                    ensure_ascii=False
                ))
                break
