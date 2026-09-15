from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "data" / "processed" / "wpi"
REPORT_FILE = OUTPUT_DIR / "wpi_normalization_report.json"

WPI_QUERY_URL = (
    "https://fgmod.nga.mil/nauticalpubs-feature/"
    "rest/services/WPI/WPI_Viewer/FeatureServer/0/query"
)
WPI_SOURCE = "NGA World Port Index"
WPI_SOURCE_URL = (
    "https://fgmod.nga.mil/nauticalpubs-feature/"
    "rest/services/WPI/WPI_Viewer/FeatureServer/0"
)
PROVENANCE = "REAL"
PAGE_SIZE = 3000
TIMEOUT = 60
MAX_RETRIES = 4

OUT_FIELDS = [
    "wpinumber",
    "main_port_name",
    "alternate_name",
    "unlocode",
    "wpi_cc",
    "regionname",
    "maxvessellength",
    "maxvesselbeam",
    "maxvesseldraft",
    "channel_depth",
    "anchorage_depth",
    "cargo_pier_depth",
    "oil_terminal_depth",
    "lng_terminal_depth",
    "fac_solidbulk",
    "fac_liquidbulk",
    "fac_container",
    "fac_breakbulk",
    "fac_roro",
    "fac_oilterm",
    "fac_lngterm",
    "fac_wharves",
    "fac_anchor",
    "com_rail",
    "railway",
    "publication",
    "publication_url",
]

CARGO_FACILITY_MAP = {
    "fac_solidbulk": "SOLID_BULK",
    "fac_liquidbulk": "LIQUID_BULK",
    "fac_container": "CONTAINER",
    "fac_breakbulk": "BREAKBULK",
    "fac_roro": "RORO",
}


def request_json(url: str) -> dict:
    headers = {
        "Accept": "application/json",
        "User-Agent": "CHARTERPULSE-AI1/WPI-loader",
    }

    last_error: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            request = Request(url, headers=headers, method="GET")
            with urlopen(request, timeout=TIMEOUT) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            last_error = RuntimeError(f"HTTP {exc.code}: {body}")
            if exc.code not in (429, 500, 502, 503, 504):
                raise last_error from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = RuntimeError(f"WPI request failed: {exc}")

        if attempt < MAX_RETRIES:
            time.sleep(min(2**attempt, 10))

    raise last_error or RuntimeError("WPI request failed.")


def normalize_unlocode(value: object) -> str | None:
    if value is None:
        return None

    normalized = "".join(str(value).strip().upper().split())
    return normalized or None


def positive_number(value: object) -> float | None:
    if value is None:
        return None

    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    return number if number > 0 else None


def yes_no(value: object) -> bool | None:
    if value is None:
        return None

    normalized = str(value).strip().lower()

    if normalized == "yes":
        return True
    if normalized == "no":
        return False

    return None


def cargo_handling_types(attrs: dict) -> list[str] | None:
    result = []

    for field, cargo_type in CARGO_FACILITY_MAP.items():
        if str(attrs.get(field) or "").strip().lower() == "yes":
            result.append(cargo_type)

    return result or None


def normalize_feature(feature: dict) -> dict:
    attrs = feature.get("attributes") or {}

    return {
        "wpi_number": attrs.get("wpinumber"),
        "port_name": attrs.get("main_port_name"),
        "alternate_name": attrs.get("alternate_name"),
        "unlocode": normalize_unlocode(attrs.get("unlocode")),
        # wpi_cc is a country NAME in the observed WPI layer despite its field alias.
        "country_name": attrs.get("wpi_cc"),
        "region_name": attrs.get("regionname"),
        "max_loa_m": positive_number(attrs.get("maxvessellength")),
        "max_beam_m": positive_number(attrs.get("maxvesselbeam")),
        "max_draft_m": positive_number(attrs.get("maxvesseldraft")),
        # Retain depth observations separately; these are not maximum vessel draft.
        "channel_depth_m": positive_number(attrs.get("channel_depth")),
        "anchorage_depth_m": positive_number(attrs.get("anchorage_depth")),
        "cargo_pier_depth_m": positive_number(attrs.get("cargo_pier_depth")),
        "oil_terminal_depth_m": positive_number(attrs.get("oil_terminal_depth")),
        "lng_terminal_depth_m": positive_number(attrs.get("lng_terminal_depth")),
        "cargo_handling_types": cargo_handling_types(attrs),
        "rail_connected": yes_no(attrs.get("com_rail")),
        "railway": attrs.get("railway"),
        "facility_oil_terminal": yes_no(attrs.get("fac_oilterm")),
        "facility_lng_terminal": yes_no(attrs.get("fac_lngterm")),
        "facility_wharves": yes_no(attrs.get("fac_wharves")),
        "facility_anchorage": yes_no(attrs.get("fac_anchor")),
        "publication": attrs.get("publication"),
        "publication_url": attrs.get("publication_url"),
        "source": WPI_SOURCE,
        "source_url": WPI_SOURCE_URL,
        "provenance": PROVENANCE,
        "observed_at": None,
    }


def fetch_all_features(limit: int | None = None) -> list[dict]:
    records: list[dict] = []
    offset = 0

    while True:
        remaining = PAGE_SIZE if limit is None else min(PAGE_SIZE, limit - len(records))
        if remaining <= 0:
            break

        params = {
            "where": "1=1",
            "outFields": ",".join(OUT_FIELDS),
            "returnGeometry": "false",
            "resultOffset": str(offset),
            "resultRecordCount": str(remaining),
            "f": "json",
        }

        payload = request_json(f"{WPI_QUERY_URL}?{urlencode(params)}")

        if payload.get("error"):
            raise RuntimeError(f"WPI query error: {payload['error']}")

        features = payload.get("features") or []
        if not features:
            break

        records.extend(normalize_feature(feature) for feature in features)
        offset += len(features)

        if limit is not None and len(records) >= limit:
            break

        if not payload.get("exceededTransferLimit") and len(features) < remaining:
            break

    return records[:limit] if limit is not None else records


def build_report(records: list[dict]) -> dict:
    unlocodes = [record["unlocode"] for record in records if record["unlocode"]]
    duplicate_unlocodes = sorted(
        {value for value in unlocodes if unlocodes.count(value) > 1}
    )

    return {
        "source": WPI_SOURCE,
        "source_url": WPI_SOURCE_URL,
        "provenance": PROVENANCE,
        "record_count": len(records),
        "missing_unlocode": sum(not record["unlocode"] for record in records),
        "duplicate_unlocodes": duplicate_unlocodes,
        "invalid_or_missing_max_loa": sum(
            record["max_loa_m"] is None for record in records
        ),
        "invalid_or_missing_max_beam": sum(
            record["max_beam_m"] is None for record in records
        ),
        "invalid_or_missing_max_draft": sum(
            record["max_draft_m"] is None for record in records
        ),
        "populated_max_loa": sum(
            record["max_loa_m"] is not None for record in records
        ),
        "populated_max_beam": sum(
            record["max_beam_m"] is not None for record in records
        ),
        "populated_max_draft": sum(
            record["max_draft_m"] is not None for record in records
        ),
        "populated_rail_connected": sum(
            record["rail_connected"] is not None for record in records
        ),
        "populated_cargo_handling": sum(
            record["cargo_handling_types"] is not None for record in records
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read and normalize NGA World Port Index data. No Supabase writes."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Read at most N WPI records.",
    )
    args = parser.parse_args()

    if args.limit is not None and args.limit <= 0:
        parser.error("--limit must be greater than zero")

    print("Source: NGA World Port Index")
    print(f"Endpoint: {WPI_QUERY_URL}")
    print("Mode: READ-ONLY / NO SUPABASE WRITES")

    records = fetch_all_features(args.limit)
    report = build_report(records)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Records normalized: {len(records)}")
    print(f"Missing UN/LOCODE: {report['missing_unlocode']}")
    print(f"Duplicate UN/LOCODEs: {len(report['duplicate_unlocodes'])}")
    print(f"Max LOA populated: {report['populated_max_loa']}")
    print(f"Max beam populated: {report['populated_max_beam']}")
    print(f"Max draft populated: {report['populated_max_draft']}")
    print(f"Rail status populated: {report['populated_rail_connected']}")
    print(f"Cargo handling populated: {report['populated_cargo_handling']}")
    print(f"Report: {REPORT_FILE}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
