from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.api.app.repositories.supabase_client import (
    get_supabase_admin_client,
)



INPUT = (
    ROOT
    / "data"
    / "processed"
    / "vessels"
    / "marinevessels_normalized.csv"
)


INSERT_COLUMNS = [
    "imo_number",
    "mmsi",
    "name",
    "vessel_class",
    "ship_type",
    "flag",
    "dwt_mt",
    "gross_tonnage",
    "loa_m",
    "beam_m",
    "max_draft_m",
    "cargo_capacity_mt",
    "year_built",
    "source",
    "source_reference",
    "provenance",
    "observed_at",
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Load eligible MarineVessels records into Supabase."
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually write records to Supabase. Default is dry-run.",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Number of rows per insert batch.",
    )

    return parser.parse_args()


def clean_record(record: dict) -> dict:
    cleaned = {}

    for column in INSERT_COLUMNS:
        value = record.get(column)

        if pd.isna(value):
            value = None

        if column in {"imo_number", "mmsi"} and value is not None:
            value = str(value).strip()

        if column == "year_built" and value is not None:
            value = int(float(value))

        cleaned[column] = value

    return cleaned


def load_candidates() -> pd.DataFrame:
    if not INPUT.exists():
        raise FileNotFoundError(
            f"Normalized MarineVessels file not found: {INPUT}"
        )

    df = pd.read_csv(
        INPUT,
        dtype={
            "imo_number": "string",
            "mmsi": "string",
        },
    )

    required = {
        "identity_classification",
        *INSERT_COLUMNS,
    }

    missing = sorted(required - set(df.columns))

    if missing:
        raise RuntimeError(
            f"Normalized dataset is missing columns: {missing}"
        )

    candidates = df[
        df["identity_classification"] == "INGESTABLE"
    ].copy()

    if candidates["name"].isna().any():
        raise RuntimeError(
            "Ingestable dataset contains vessels without names."
        )

    if candidates["imo_number"].dropna().duplicated().any():
        raise RuntimeError(
            "Duplicate IMO detected in ingestable candidates."
        )

    if candidates["mmsi"].dropna().duplicated().any():
        raise RuntimeError(
            "Duplicate MMSI detected in ingestable candidates."
       )

    return candidates


def existing_identity_sets(client):
    rows = []

    response = (
        client
        .table("vessels")
        .select("id,imo_number,mmsi,source,provenance")
        .execute()
    )

    rows.extend(response.data or [])

    existing_imo = {
        str(row["imo_number"])
        for row in rows
        if row.get("imo_number") is not None
    }

    existing_mmsi = {
        str(row["mmsi"])
        for row in rows
        if row.get("mmsi") is not None
    }

    return rows, existing_imo, existing_mmsi


def main():
    args = parse_args()

    candidates = load_candidates()

    print("MarineVessels Supabase loader")
    print("-----------------------------")
    print(f"Candidate rows: {len(candidates)}")
    print(f"Mode: {'APPLY' if args.apply else 'DRY-RUN'}")
    print(f"Batch size: {args.batch_size}")
    print()

    client = get_supabase_admin_client()

    existing_rows, existing_imo, existing_mmsi = (
        existing_identity_sets(client)
    )

    print(f"Existing vessels: {len(existing_rows)}")
    print(f"Existing IMO values: {len(existing_imo)}")
    print(f"Existing MMSI values: {len(existing_mmsi)}")
    print()

    insert_rows = []
    skip_existing = 0
    conflict_count = 0

    for record in candidates.to_dict(orient="records"):
        imo = record.get("imo_number")
        mmsi = record.get("mmsi")

        imo = None if pd.isna(imo) else str(imo).strip()
        mmsi = None if pd.isna(mmsi) else str(mmsi).strip()

        imo_exists = imo is not None and imo in existing_imo
        mmsi_exists = mmsi is not None and mmsi in existing_mmsi

        if imo_exists or mmsi_exists:
            skip_existing += 1
            continue

        if imo is None and mmsi is None:
            conflict_count += 1
            continue

        insert_rows.append(clean_record(record))

    print("--- PLAN ---")
    print(f"New records:        {len(insert_rows)}")
    print(f"Already existing:   {skip_existing}")
    print(f"Identity conflicts: {conflict_count}")
    print()

    if not args.apply:
        print("DRY-RUN COMPLETE.")
        print("SUPABASE WRITES: NONE")
        return

    inserted = 0

    for start in range(0, len(insert_rows), args.batch_size):
        batch = insert_rows[start:start + args.batch_size]

        client.table("vessels").insert(batch).execute()

        inserted += len(batch)

        print(
            f"Inserted {inserted}/{len(insert_rows)}"
        )

    print()
    print("MarineVessels ingestion committed.")
    print(f"Inserted: {inserted}")
    print(f"Skipped existing: {skip_existing}")
    print(f"Identity conflicts: {conflict_count}")


if __name__ == "__main__":
    main()
