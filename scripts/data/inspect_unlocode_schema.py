import json
import os
from urllib.request import Request, urlopen

env_file = ".env"

for line in open(env_file, encoding="utf-8"):
    line = line.strip()

    if not line or line.startswith("#") or "=" not in line:
        continue

    key, value = line.split("=", 1)
    value = value.strip().strip('"').strip("'")
    os.environ.setdefault(key.strip(), value)

base = os.environ["SUPABASE_URL"].rstrip("/")
key = os.environ["SUPABASE_SECRET_KEY"]

url = f"{base}/rest/v1/"

request = Request(
    url,
    headers={
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Accept": "application/openapi+json",
    },
)

with urlopen(request, timeout=30) as response:
    schema = json.loads(response.read().decode("utf-8"))

definition = (
    schema
    .get("definitions", {})
    .get("unlocode_source_records")
)

if not definition:
    print("ERROR: unlocode_source_records was not found in Supabase schema.")
    print("Available matching definitions:")
    for name in sorted(schema.get("definitions", {})):
        if "unlocode" in name.lower():
            print("  ", name)
    raise SystemExit(1)

print("=" * 72)
print("REMOTE SUPABASE SCHEMA: unlocode_source_records")
print("=" * 72)

properties = definition.get("properties", {})

for name, info in properties.items():
    print(f"{name:<32} {info.get('type', '?')}")

print()
print(f"Column count: {len(properties)}")
print("=" * 72)
