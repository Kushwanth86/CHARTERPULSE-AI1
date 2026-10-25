from __future__ import annotations

import argparse
import csv
import math
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.api.app.repositories.supabase_client import (
    get_supabase_admin_client,
    get_supabase_client,
)


SCHEMA_VERSION = "1"
METRIC = "freight_rate"
UNIT = "USD/MT"
CURRENCY = "USD"
ALLOWED_PROVENANCE = {"REAL", "PUBLIC_PROXY", "USER_PROVIDED", "DERIVED"}
UNLOCODE_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{3}$")
VESSEL_CLASS_RE = re.compile(r"^[A-Za-z][A-Za-z0-9 -]{0,63}$")
REQUIRED_COLUMNS = {
    "origin_unlocode",
    "destination_unlocode",
    "vessel_class",
    "market_type",
    "metric",
    "value",
    "unit",
    "currency",
    "observed_at",
    "retrieved_at",
    "source",
    "source_record_id",
    "source_reference",
    "provenance",
}


def parse_timestamp(value: str, *, column: str, row_number: int) -> str:
    raw = (value or "").strip()
    if not raw:
        raise ValueError(f"row {row_number}: {column} is required")

    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(
            f"row {row_number}: {column} must be an ISO-8601 timestamp"
        ) from exc

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(
            f"row {row_number}: {column} must include a timezone (for example, Z)"
        )

    return (
        parsed.astimezone(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
        .replace(".000000Z", "Z")
    )


def parse_csv(path: str | Path) -> list[dict[str, Any]]:
    """Read and strictly validate source-backed, route-specific freight observations.

    This importer intentionally accepts only USD per metric tonne. Do not convert
    index points, USD/day, or a different route into USD/MT without a documented,
    tested transformation and appropriate source provenance.
    """
    csv_path = Path(path)
    if not csv_path.is_file():
        raise FileNotFoundError(f"Input CSV not found: {csv_path}")

    records: list[dict[str, Any]] = []
    seen_records: dict[tuple[str, str], int] = {}

    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = {str(value or "").strip() for value in (reader.fieldnames or [])}
        missing = sorted(REQUIRED_COLUMNS - headers)
        if missing:
            raise ValueError(f"CSV is missing required columns: {', '.join(missing)}")

        for row_number, raw_row in enumerate(reader, start=2):
            row = {
                str(key).strip(): str(value or "").strip()
                for key, value in raw_row.items()
                if key is not None
            }

            if not any(row.values()):
                continue

            origin = row.get("origin_unlocode", "").upper()
            destination = row.get("destination_unlocode", "").upper()
            if not UNLOCODE_RE.fullmatch(origin):
                raise ValueError(
                    f"row {row_number}: invalid origin UN/LOCODE {origin!r}"
                )
            if not UNLOCODE_RE.fullmatch(destination):
                raise ValueError(
                    f"row {row_number}: invalid destination UN/LOCODE {destination!r}"
                )
            if origin == destination:
                raise ValueError(
                    f"row {row_number}: origin and destination must be different"
                )

            vessel_class = row.get("vessel_class", "")
            if not VESSEL_CLASS_RE.fullmatch(vessel_class):
                raise ValueError(
                    f"row {row_number}: invalid or missing vessel_class"
                )

            metric = row.get("metric", "").lower()
            if metric != METRIC:
                raise ValueError(
                    f"row {row_number}: metric must be {METRIC!r}; got {metric!r}"
                )

            unit = row.get("unit", "").upper().replace(" ", "")
            currency = row.get("currency", "").upper()
            if unit != UNIT or currency != CURRENCY:
                raise ValueError(
                    f"row {row_number}: expected unit={UNIT!r} and "
                    f"currency={CURRENCY!r}; got unit={unit!r}, currency={currency!r}"
                )

            raw_value = row.get("value", "")
            try:
                value = float(raw_value)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"row {row_number}: value must be a number"
                ) from exc
            if not math.isfinite(value) or value <= 0:
                raise ValueError(
                    f"row {row_number}: value must be finite and greater than zero"
                )

            market_type = row.get("market_type", "").strip()
            source = row.get("source", "").strip()
            source_record_id = row.get("source_record_id", "").strip()
            source_reference = row.get("source_reference", "").strip()
            if not market_type:
                raise ValueError(f"row {row_number}: market_type is required")
            if not source:
                raise ValueError(f"row {row_number}: source is required")
            if not source_record_id:
                raise ValueError(f"row {row_number}: source_record_id is required")
            if not source_reference:
                raise ValueError(f"row {row_number}: source_reference is required")

            provenance = row.get("provenance", "").upper()
            if provenance not in ALLOWED_PROVENANCE:
                allowed = ", ".join(sorted(ALLOWED_PROVENANCE))
                raise ValueError(
                    f"row {row_number}: provenance must be one of {allowed}; "
                    f"{provenance!r} is not accepted for production ingestion"
                )

            if not row.get("observed_at"):
                raise ValueError(f"row {row_number}: observed_at is required")
            observed_at = parse_timestamp(
                row["observed_at"], column="observed_at", row_number=row_number
            )
            retrieved_at = parse_timestamp(
                row["retrieved_at"], column="retrieved_at", row_number=row_number
            )

            # A source record ID is the stable identity used for idempotent imports.
            source_identity = (source.casefold(), source_record_id)
            previous_row = seen_records.get(source_identity)
            if previous_row is not None:
                raise ValueError(
                    f"row {row_number}: duplicate source_record_id for source "
                    f"{source!r}; first seen on row {previous_row}"
                )
            seen_records[source_identity] = row_number

            records.append(
                {
                    "origin_unlocode": origin,
                    "destination_unlocode": destination,
                    "vessel_class": vessel_class,
                    "market_type": market_type,
                    "metric": METRIC,
                    "value": value,
                    "unit": UNIT,
                    "currency": CURRENCY,
                    "observed_at": observed_at,
                    "retrieved_at": retrieved_at,
                    "source": source,
                    "source_record_id": source_record_id,
                    "source_reference": source_reference,
                    "provenance": provenance,
                    "_row_number": row_number,
                }
            )

    if not records:
        raise ValueError("CSV contains no freight observations to ingest")

    return records


def resolve_locations(client, unlocodes: set[str]) -> dict[str, dict[str, str]]:
    """Resolve UN/LOCODE identifiers to the exact canonical locations table IDs."""
    result = (
        client.table("locations")
        .select("id,unlocode,name")
        .in_("unlocode", sorted(unlocodes))
        .execute()
    )

    mapping: dict[str, dict[str, str]] = {}
    for row in result.data or []:
        code = str(row.get("unlocode") or "").strip().upper()
        if not code:
            continue
        if code in mapping:
            raise ValueError(
                f"Database has multiple locations for UN/LOCODE {code}; "
                "resolve the identity before importing freight observations."
            )
        mapping[code] = {
            "id": str(row["id"]),
            "name": str(row.get("name") or code),
        }

    missing = sorted(unlocodes - set(mapping))
    if missing:
        raise ValueError(
            "The following source route UN/LOCODEs do not resolve to canonical "
            f"locations: {', '.join(missing)}. Do not substitute nearby ports."
        )

    return mapping


def build_payloads(
    records: list[dict[str, Any]],
    locations: dict[str, dict[str, str]],
    *,
    input_filename: str,
) -> list[dict[str, Any]]:
    payloads = []
    for record in records:
        origin = locations[record["origin_unlocode"]]
        destination = locations[record["destination_unlocode"]]
        payloads.append(
            {
                "origin_location_id": origin["id"],
                "destination_location_id": destination["id"],
                "vessel_class": record["vessel_class"],
                "market_type": record["market_type"],
                "metric": record["metric"],
                "value": record["value"],
                "unit": record["unit"],
                "currency": record["currency"],
                "observed_at": record["observed_at"],
                "retrieved_at": record["retrieved_at"],
                "source": record["source"],
                "source_record_id": record["source_record_id"],
                "source_reference": record["source_reference"],
                "provenance": record["provenance"],
                "metadata": {
                    "ingestion_pipeline": "source-backed-freight-csv",
                    "schema_version": SCHEMA_VERSION,
                    "input_filename": Path(input_filename).name,
                    "input_row_number": record["_row_number"],
                    "route_identity": {
                        "origin_unlocode": record["origin_unlocode"],
                        "destination_unlocode": record["destination_unlocode"],
                    },
                    "normalization": {
                        "timestamp_timezone": "UTC",
                        "value_unit": UNIT,
                        "route_mapping": "Exact UN/LOCODE to public.locations.id",
                    },
                },
            }
        )
    return payloads


def observation_identity(row: dict[str, Any]) -> tuple[str, ...]:
    return (
        str(row.get("origin_location_id") or ""),
        str(row.get("destination_location_id") or ""),
        str(row.get("vessel_class") or "").strip().casefold(),
        str(row.get("metric") or "").strip().lower(),
        str(row.get("observed_at") or ""),
        str(row.get("source") or "").strip().casefold(),
        str(row.get("source_record_id") or "").strip(),
    )


def prepare_insert_plan(
    payloads: list[dict[str, Any]],
    existing_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    """Skip exact replays; fail closed if a source record ID conflicts."""
    existing: dict[tuple[str, ...], dict[str, Any]] = {}
    for row in existing_rows:
        identity = observation_identity(row)
        if identity in existing:
            raise ValueError(
                "Database already contains duplicate source observation identities; "
                "resolve duplicates before ingesting more data."
            )
        existing[identity] = row

    inserts: list[dict[str, Any]] = []
    skipped = 0
    for payload in payloads:
        identity = observation_identity(payload)
        prior = existing.get(identity)
        if prior is None:
            inserts.append(payload)
            # Catch repeated identities within the input plan as well.
            existing[identity] = payload
            continue

        same_observation = (
            math.isclose(
                float(prior.get("value")),
                float(payload["value"]),
                rel_tol=0,
                abs_tol=1e-9,
            )
            and str(prior.get("unit") or "") == payload["unit"]
            and str(prior.get("currency") or "") == payload["currency"]
            and str(prior.get("source_reference") or "") == payload["source_reference"]
            and str(prior.get("provenance") or "").upper() == payload["provenance"]
        )
        if not same_observation:
            raise ValueError(
                "Source record identity already exists with different observation "
                f"data: source={payload['source']!r}, "
                f"source_record_id={payload['source_record_id']!r}. "
                "Do not overwrite historical observations silently."
            )
        skipped += 1

    return inserts, skipped


def existing_route_observations(
    client,
    payloads: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], None] = {}
    for row in payloads:
        groups[
            (
                row["origin_location_id"],
                row["destination_location_id"],
                row["vessel_class"],
            )
        ] = None

    existing: list[dict[str, Any]] = []
    columns = (
        "origin_location_id,destination_location_id,vessel_class,metric,value,"
        "unit,currency,observed_at,source,source_record_id,source_reference,provenance"
    )

    for origin_id, destination_id, vessel_class in groups:
        query = (
            client.table("market_observations")
            .select(columns)
            .eq("origin_location_id", origin_id)
            .eq("destination_location_id", destination_id)
            .ilike("vessel_class", vessel_class)
            .eq("metric", METRIC)
        )
        response = query.limit(5000).execute()
        existing.extend(response.data or [])

    return existing


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate and ingest source-backed route-specific freight observations. "
            "Default is a read-only dry run; --apply is required for database writes."
        )
    )
    parser.add_argument("--csv", required=True, help="Source data CSV file.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Insert eligible records into Supabase. Without this flag, no rows are written.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Rows per insert batch when --apply is specified (1-500).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not 1 <= args.batch_size <= 500:
        raise ValueError("--batch-size must be between 1 and 500")

    records = parse_csv(args.csv)
    unlocodes = {
        code
        for record in records
        for code in (record["origin_unlocode"], record["destination_unlocode"])
    }

    # Dry-run uses the non-privileged client for location resolution and read-only
    # duplicate checks. Privileged credentials are requested only with --apply.
    read_client = get_supabase_client()
    locations = resolve_locations(read_client, unlocodes)
    payloads = build_payloads(records, locations, input_filename=args.csv)

    try:
        existing = existing_route_observations(read_client, payloads)
    except Exception as exc:
        raise RuntimeError(
            "Could not read market-observation source identity fields. "
            "Apply supabase/migrations/037_source_backed_freight_ingestion.sql "
            "before running this importer."
        ) from exc

    inserts, skipped = prepare_insert_plan(payloads, existing)

    print("Source-backed freight observation ingestion")
    print("-------------------------------------------")
    print(f"Input rows:            {len(records)}")
    print(f"Resolved route codes:  {len(unlocodes)}")
    print(f"Already imported:      {skipped}")
    print(f"Rows to insert:        {len(inserts)}")
    print(f"Mode:                  {'APPLY' if args.apply else 'DRY-RUN'}")
    print("Forecast metric/unit:  freight_rate / USD/MT")
    print("Synthetic inputs:      REJECTED")
    print()

    if not args.apply:
        print("DRY-RUN COMPLETE. DATABASE WRITES: NONE")
        return 0

    write_client = get_supabase_admin_client()
    inserted = 0
    for start in range(0, len(inserts), args.batch_size):
        batch = inserts[start : start + args.batch_size]
        try:
            write_client.table("market_observations").insert(batch).execute()
        except Exception as exc:
            raise RuntimeError(
                f"Insert batch beginning at planned record {start + 1} failed. "
                "Earlier batches, if any, may already be committed; rerun the "
                "same CSV after resolving the error to safely skip exact replays."
            ) from exc
        inserted += len(batch)
        print(f"Inserted {inserted}/{len(inserts)}")

    print()
    print("INGESTION COMPLETE")
    print(f"Inserted:              {inserted}")
    print(f"Skipped exact replays: {skipped}")
    print("Run the route-specific forecast endpoint only after reviewing these records.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
