import json
import os
from urllib.request import Request, urlopen

for line in open(".env", encoding="utf-8"):
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue

    key, value = line.split("=", 1)
    value = value.strip().strip('"').strip("'")
    os.environ.setdefault(key.strip(), value)

base = os.environ["SUPABASE_URL"].rstrip("/")
secret = os.environ["SUPABASE_SECRET_KEY"]

request = Request(
    f"{base}/rest/v1/",
    headers={
        "apikey": secret,
        "Authorization": f"Bearer {secret}",
        "Accept": "application/openapi+json",
    },
)

with urlopen(request, timeout=30) as response:
    schema = json.loads(response.read().decode("utf-8"))

for table in [
    "countries",
    "locations",
    "unlocode_locations",
    "unlocode_source_relationships",
]:
    definition = schema.get("definitions", {}).get(table)

    print()
    print("=" * 72)
    print(table)
    print("=" * 72)

    if not definition:
        print("NOT FOUND")
        continue

    properties = definition.get("properties", {})

    for name, info in properties.items():
        print(f"{name:<35} {info.get('type', '?')}")

    print(f"Columns: {len(properties)}")
