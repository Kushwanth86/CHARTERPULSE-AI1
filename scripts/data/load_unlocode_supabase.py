from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = ROOT / "data" / "processed" / "unlocode"

COUNTRIES_FILE = DATA_DIR / "countries.jsonl"
SOURCE_FILE = DATA_DIR / "unlocode_source_records.jsonl"
CANONICAL_FILE = DATA_DIR / "unlocode_canonical.jsonl"
DUPLICATES_FILE = DATA_DIR / "unlocode_duplicates.jsonl"

SOURCE = "UNECE UN/LOCODE"
SOURCE_VERSION = "2025-1"
SOURCE_URL = "https://unece.org/trade/cefact/UNLOCODE-Download"
PROVENANCE = "REAL"

BATCH_SIZE = 100
TIMEOUT = 60
MAX_RETRIES = 4

UUID_NAMESPACE = uuid.UUID("4b9a8e72-7f9d-4b5f-a8e8-3c5d1e8a7a11")


def load_env():
    env_file = ROOT / ".env"

    if not env_file.exists():
        raise RuntimeError(f".env not found: {env_file}")

    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in ("'", '"')
        ):
            value = value[1:-1]

        os.environ.setdefault(key, value)


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()

    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")

    return value


def deterministic_uuid(kind: str, *parts: object) -> str:
    material = "|".join(
        "" if value is None else str(value)
        for value in (kind, *parts)
    )

    return str(uuid.uuid5(UUID_NAMESPACE, material))


def read_jsonl(path: Path):
    if not path.exists():
        raise FileNotFoundError(path)

    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    f"Invalid JSON at {path}:{line_no}: {exc}"
                ) from exc


def batched(items, size):
    batch = []

    for item in items:
        batch.append(item)

        if len(batch) >= size:
            yield batch
            batch = []

    if batch:
        yield batch


class Supabase:
    def __init__(self):
        load_env()

        self.url = require_env("SUPABASE_URL").rstrip("/")
        self.key = (
            os.environ.get("SUPABASE_SECRET_KEY", "").strip()
            or os.environ.get("SUPABASE_PUBLISHABLE_KEY", "").strip()
        )

        if not self.key:
            raise RuntimeError(
                "Neither SUPABASE_SECRET_KEY nor SUPABASE_PUBLISHABLE_KEY is configured."
            )

        self.base = f"{self.url}/rest/v1"

    def request(self, table, method="GET", params=None, payload=None):
        url = f"{self.base}/{table}"

        if params:
            url += "?" + urlencode(params)

        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
        }

        if method in ("POST", "PATCH", "PUT"):
            headers["Prefer"] = "resolution=merge-duplicates,return=minimal"

        body = None

        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        last_error = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                request = Request(
                    url,
                    data=body,
                    headers=headers,
                    method=method,
                )

                with urlopen(request, timeout=TIMEOUT) as response:
                    raw = response.read().decode("utf-8")

                    if not raw:
                        return None

                    try:
                        return json.loads(raw)
                    except json.JSONDecodeError:
                        return raw

            except HTTPError as exc:
                response_body = exc.read().decode("utf-8", errors="replace")

                if exc.code in (429, 500, 502, 503, 504):
                    last_error = RuntimeError(
                        f"HTTP {exc.code}: {response_body}"
                    )
                    time.sleep(min(2 ** attempt, 10))
                    continue

                raise RuntimeError(
                    f"HTTP {exc.code}: {response_body}"
                ) from exc

            except URLError as exc:
                last_error = RuntimeError(
                    f"Network error: {exc}"
                )
                time.sleep(min(2 ** attempt, 10))

        raise last_error or RuntimeError("Supabase request failed.")


def upsert_batches(client, table, rows):
    rows = list(rows)

    if not rows:
        return 0

    total = 0

    for batch in batched(rows, BATCH_SIZE):
        client.request(
            table,
            method="POST",
            params={"on_conflict": "id"},
            payload=batch,
        )

        total += len(batch)
        print(f"  {table}: {total} rows processed")

    return total


def country_fields(record):
    iso2 = (
        record.get("iso2")
        or record.get("country_code")
        or record.get("country")
        or record.get("code")
    )

    iso3 = (
        record.get("iso3")
        or record.get("iso3_code")
    )

    name = (
        record.get("name")
        or record.get("country_name")
        or record.get("country")
    )

    if isinstance(iso2, str):
        iso2 = iso2.strip().upper()

    if isinstance(iso3, str):
        iso3 = iso3.strip().upper()

    if isinstance(name, str):
        name = name.strip()

    return iso2, iso3, name


def load_countries(client):
    print("\n[1/5] Loading countries...")

    rows = []
    country_map = {}

    for record in read_jsonl(COUNTRIES_FILE):
        iso2, iso3, name = country_fields(record)

        if not iso2 or not name:
            continue

        country_id = deterministic_uuid("country", iso2)

        row = {
            "id": country_id,
            "iso2": iso2,
            "iso3": iso3,
            "name": name,
            "source": record.get("source") or SOURCE,
            "source_url": record.get("source_url") or SOURCE_URL,
            "observed_at": record.get("observed_at"),
        }

        rows.append(row)
        country_map[iso2] = country_id

    print(f"  Countries prepared: {len(rows)}")

    upsert_batches(client, "countries", rows)

    print(f"  Country mappings available: {len(country_map)}")

    return country_map


def source_record_to_row(record):
    source_record_id = record.get("source_record_id")

    if not source_record_id:
        raise RuntimeError("Source record missing source_record_id")

    country = record.get("country")
    location = record.get("location")

    if isinstance(country, str):
        country = country.strip().upper()

    if isinstance(location, str):
        location = location.strip().upper()

    row = {
        "id": deterministic_uuid(
            "source_record",
            SOURCE,
            SOURCE_VERSION,
            source_record_id,
        ),
        "source": record.get("source") or SOURCE,
        "source_version": record.get("source_version") or SOURCE_VERSION,
        "source_record_id": source_record_id,
        "record_type": record.get("record_type"),
        "locode": record.get("locode"),
        "country_code": country,
        "location_code": location,
        "change_code": record.get("change"),
        "name": record.get("name"),
        "name_wo_diacritics": record.get("name_wo_diacritics"),
        "subdiv": record.get("subdiv"),
        "function": record.get("function"),
        "status": record.get("status"),
        "date_code": record.get("date"),
        "iata": record.get("iata"),
        "coordinates_raw": record.get("coordinates"),
        "latitude": record.get("latitude"),
        "longitude": record.get("longitude"),
        "coordinate_quality": record.get("coordinate_quality"),
        "remarks": record.get("remarks"),
        "source_file": record.get("source_file"),
        "source_line": record.get("source_line"),
        "provenance": record.get("provenance") or PROVENANCE,
        "observed_at": record.get("observed_at"),
    }

    return row


def load_source_records(client, target_ids=None):
    print("\n[2/5] Loading source records...")

    rows = []
    found = set()

    for record in read_jsonl(SOURCE_FILE):
        source_record_id = record.get("source_record_id")

        if target_ids is not None and source_record_id not in target_ids:
            continue

        rows.append(source_record_to_row(record))

        if source_record_id:
            found.add(source_record_id)

        if target_ids is not None and found >= target_ids:
            break

    print(f"  Source records prepared: {len(rows)}")

    upsert_batches(client, "unlocode_source_records", rows)

    return found


def canonical_to_unlocode_row(record, country_map):
    locode = record.get("locode")

    if not locode:
        raise RuntimeError("Canonical record missing locode")

    country_code = record.get("country")

    if isinstance(country_code, str):
        country_code = country_code.strip().upper()

    location_code = record.get("location")

    if isinstance(location_code, str):
        location_code = location_code.strip().upper()

    country_id = country_map.get(country_code)

    source_record_id = record.get("source_record_id")

    return {
        "id": deterministic_uuid(
            "unlocode_location",
            SOURCE,
            SOURCE_VERSION,
            locode,
        ),
        "locode": locode,
        "country_code": country_code,
        "location_code": location_code,
        "country_id": country_id,
        "name": record.get("name"),
        "name_wo_diacritics": record.get("name_wo_diacritics"),
        "subdiv": record.get("subdiv"),
        "function": record.get("function"),
        "status": record.get("status"),
        "date_code": record.get("date"),
        "iata": record.get("iata"),
        "coordinates_raw": record.get("coordinates"),
        "latitude": record.get("latitude"),
        "longitude": record.get("longitude"),
        "coordinate_quality": record.get("coordinate_quality"),
        "canonical_source_record_id": deterministic_uuid(
            "source_record",
            SOURCE,
            SOURCE_VERSION,
            source_record_id,
        ),
        "source": record.get("source") or SOURCE,
        "source_version": record.get("source_version") or SOURCE_VERSION,
        "provenance": record.get("provenance") or PROVENANCE,
        "observed_at": record.get("observed_at"),
    }


def canonical_to_location_row(record, country_map):
    locode = record.get("locode")
    country_code = record.get("country")

    if isinstance(country_code, str):
        country_code = country_code.strip().upper()

    source_record_id = record.get("source_record_id")

    return {
        "id": deterministic_uuid(
            "location",
            SOURCE,
            SOURCE_VERSION,
            locode,
        ),
        "country_id": country_map.get(country_code),
        "region_id": None,
        "name": record.get("name"),
        "latitude": record.get("latitude"),
        "longitude": record.get("longitude"),
        "timezone": None,
        "source": record.get("source") or SOURCE,
        "source_url": SOURCE_URL,
        "observed_at": record.get("observed_at"),
        "unlocode": locode,
        "unlocode_source_record_id": deterministic_uuid(
            "source_record",
            SOURCE,
            SOURCE_VERSION,
            source_record_id,
        ),
        "name_wo_diacritics": record.get("name_wo_diacritics"),
        "subdiv": record.get("subdiv"),
        "function": record.get("function"),
        "status": record.get("status"),
        "iata": record.get("iata"),
        "coordinates_raw": record.get("coordinates"),
        "coordinate_quality": record.get("coordinate_quality"),
        "source_version": record.get("source_version") or SOURCE_VERSION,
    }


def load_canonical_and_locations(client, country_map, limit=None):
    print("\n[3/5] Loading canonical UN/LOCODE locations...")

    canonical_rows = []
    location_rows = []
    selected = []

    for record in read_jsonl(CANONICAL_FILE):
        if not record.get("locode"):
            continue

        selected.append(record)

        canonical_rows.append(
            canonical_to_unlocode_row(record, country_map)
        )

        location_rows.append(
            canonical_to_location_row(record, country_map)
        )

        if limit is not None and len(selected) >= limit:
            break

    print(f"  Canonical rows prepared: {len(canonical_rows)}")

    upsert_batches(
        client,
        "unlocode_locations",
        canonical_rows,
    )

    print("\n[4/5] Loading canonical rows into locations...")

    print(f"  Location rows prepared: {len(location_rows)}")

    upsert_batches(
        client,
        "locations",
        location_rows,
    )

    return selected


def relationship_to_row(record):
    locode = record.get("locode")
    canonical_id = record.get("canonical_source_record_id")
    related_id = record.get("related_source_record_id")

    return {
        "id": deterministic_uuid(
            "relationship",
            SOURCE,
            SOURCE_VERSION,
            locode,
            canonical_id,
            related_id,
        ),
        "locode": locode,
        "canonical_source_record_id": deterministic_uuid(
            "source_record",
            SOURCE,
            SOURCE_VERSION,
            canonical_id,
        ),
        "related_source_record_id": deterministic_uuid(
            "source_record",
            SOURCE,
            SOURCE_VERSION,
            related_id,
        ),
        "relationship": record.get("relationship"),
        "source": record.get("source") or SOURCE,
        "source_version": record.get("source_version") or SOURCE_VERSION,
        "observed_at": record.get("observed_at"),
    }


def load_relationships(client):
    print("\n[5/5] Loading duplicate/history relationships...")

    rows = []

    for record in read_jsonl(DUPLICATES_FILE):
        rows.append(relationship_to_row(record))

    print(f"  Relationships prepared: {len(rows)}")

    upsert_batches(
        client,
        "unlocode_source_relationships",
        rows,
    )

    return len(rows)


def get_first_canonical():
    for record in read_jsonl(CANONICAL_FILE):
        if record.get("locode"):
            return record

    raise RuntimeError("No canonical LOCODE record found.")


def smoke(client):
    print("\n========================================")
    print("UN/LOCODE ONE-ROW SMOKE TEST")
    print("========================================")

    canonical = get_first_canonical()

    locode = canonical["locode"]
    source_record_id = canonical["source_record_id"]
    country_code = canonical.get("country")

    print(f"\nSelected LOCODE : {locode}")
    print(f"Country         : {country_code}")
    print(f"Name            : {canonical.get('name')}")
    print(f"Source record   : {source_record_id}")

    country_map = load_countries(client)

    if country_code not in country_map:
        raise RuntimeError(
            f"Country {country_code} not found in countries.jsonl"
        )

    found = load_source_records(
        client,
        target_ids={source_record_id},
    )

    if source_record_id not in found:
        raise RuntimeError(
            f"Could not find source record {source_record_id}"
        )

    selected = load_canonical_and_locations(
        client,
        country_map,
        limit=1,
    )

    if not selected:
        raise RuntimeError("Canonical smoke row was not loaded.")

    print("\nSmoke test write completed.")

    print("\nChecking REST API...")

    checks = [
        (
            "countries",
            {
                "select": "id,iso2,name",
                "iso2": f"eq.{country_code}",
                "limit": "1",
            },
        ),
        (
            "unlocode_source_records",
            {
                "select": "id,locode,source_record_id,change_code",
                "source_record_id": f"eq.{source_record_id}",
                "limit": "1",
            },
        ),
        (
            "unlocode_locations",
            {
                "select": "id,locode,name,date_code,country_id",
                "locode": f"eq.{locode}",
                "limit": "1",
            },
        ),
        (
            "locations",
            {
                "select": "id,unlocode,name,country_id,coordinate_quality",
                "unlocode": f"eq.{locode}",
                "limit": "1",
            },
        ),
    ]

    for table, params in checks:
        result = client.request(
            table,
            method="GET",
            params=params,
        )

        if not result:
            raise RuntimeError(
                f"Verification failed: {table} returned no rows."
            )

        print(f"  [OK] {table}")

    print("\n========================================")
    print("SMOKE TEST PASSED")
    print("========================================")
    print(f"Verified LOCODE: {locode}")
    print("Country -> source record -> canonical -> locations")
    print("All required REST reads succeeded.")
    print("\nFull ingestion has NOT been started.")


def full(client):
    print("\n========================================")
    print("FULL UNECE UN/LOCODE INGESTION")
    print("========================================")

    country_map = load_countries(client)

    load_source_records(client)

    load_canonical_and_locations(
        client,
        country_map,
        limit=None,
    )

    load_relationships(client)

    print("\n========================================")
    print("FULL INGESTION COMPLETED")
    print("========================================")


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Run one-row smoke test only.",
    )

    parser.add_argument(
        "--full",
        action="store_true",
        help="Run complete UNECE ingestion.",
    )

    args = parser.parse_args()

    if args.smoke == args.full:
        parser.error(
            "Specify exactly one of --smoke or --full"
        )

    print("CHARTERPULSE AI - UN/LOCODE Loader")
    print(f"Root       : {ROOT}")
    print(f"Data       : {DATA_DIR}")
    print(f"Source     : {SOURCE}")
    print(f"Version    : {SOURCE_VERSION}")

    client = Supabase()

    if args.smoke:
        smoke(client)
    else:
        full(client)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)
    except Exception as exc:
        print("\nERROR:", exc)
        sys.exit(1)
