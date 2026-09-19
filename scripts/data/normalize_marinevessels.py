from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pyreadr


ROOT = Path(__file__).resolve().parents[2]

INPUT = (
    ROOT
    / "data"
    / "sources"
    / "vessels"
    / "marinevessels"
    / "data"
    / "MarineVessels.rda"
)

OUTPUT_DIR = ROOT / "data" / "processed" / "vessels"

NORMALIZED_OUTPUT = OUTPUT_DIR / "marinevessels_normalized.csv"
REPORT_OUTPUT = OUTPUT_DIR / "marinevessels_validation_report.json"
AMBIGUOUS_OUTPUT = OUTPUT_DIR / "marinevessels_ambiguous_identity.csv"


def clean_text(value):
    if pd.isna(value):
        return None

    value = str(value).strip()

    return value if value else None


def clean_positive_number(value):
    if pd.isna(value):
        return None

    try:
        value = float(value)
    except (TypeError, ValueError):
        return None

    return value if value > 0 else None


def clean_integer(value):
    if pd.isna(value):
        return None

    try:
        value = int(float(value))
    except (TypeError, ValueError):
        return None

    return value if value > 0 else None


def normalize_imo(value):
    value = clean_text(value)

    if value is None:
        return None

    digits = "".join(ch for ch in value if ch.isdigit())

    return digits if len(digits) == 7 else None


def normalize_mmsi(value):
    value = clean_text(value)

    if value is None:
        return None

    digits = "".join(ch for ch in value if ch.isdigit())

    return digits if len(digits) == 9 else None


def valid_dimension(value, maximum):
    value = clean_positive_number(value)

    if value is None:
        return None

    return value if value <= maximum else None


def load_source():
    if not INPUT.exists():
        raise FileNotFoundError(f"MarineVessels source not found: {INPUT}")

    result = pyreadr.read_r(str(INPUT))

    if not result:
        raise RuntimeError("MarineVessels RDA contained no objects.")

    return next(iter(result.values())).copy()


def normalize(df: pd.DataFrame):
    rows = []

    stats = {
        "source_rows": len(df),
        "invalid_imo": 0,
        "invalid_mmsi": 0,
        "invalid_draught": 0,
        "invalid_length": 0,
        "invalid_beam": 0,
    }

    for _, row in df.iterrows():
        imo_raw = row.get("IMO")
        mmsi_raw = row.get("MMSI")

        imo = normalize_imo(imo_raw)
        mmsi = normalize_mmsi(mmsi_raw)

        if clean_text(imo_raw) is not None and imo is None:
            stats["invalid_imo"] += 1

        if clean_text(mmsi_raw) is not None and mmsi is None:
            stats["invalid_mmsi"] += 1

        draught_raw = row.get("ship_draught")
        length_raw = row.get("length")
        beam_raw = row.get("beam")

        draught = valid_dimension(draught_raw, 30.0)
        length = valid_dimension(length_raw, 500.0)
        beam = valid_dimension(beam_raw, 80.0)

        if clean_positive_number(draught_raw) is not None and draught is None:
            stats["invalid_draught"] += 1

        if clean_positive_number(length_raw) is not None and length is None:
            stats["invalid_length"] += 1

        if clean_positive_number(beam_raw) is not None and beam is None:
            stats["invalid_beam"] += 1

        rows.append(
            {
                "imo_number": imo,
                "mmsi": mmsi,
                "name": clean_text(row.get("name")),
                "vessel_class": clean_text(row.get("type")),
                "ship_type": clean_text(row.get("type")),
                "flag": None,
                "dwt_mt": clean_positive_number(row.get("DWT")),
                "gross_tonnage": clean_positive_number(row.get("GT")),
                "loa_m": length,
                "beam_m": beam,
                "max_draft_m": draught,
                "cargo_capacity_mt": None,
                "year_built": clean_integer(row.get("built")),
                "source": "MarineVessels",
                "source_reference": (
                    "https://github.com/rich-iannone/MarineVessels"
                ),
                "provenance": "PUBLIC_PROXY",
                "observed_at": None,
            }
        )

    return pd.DataFrame(rows), stats


def classify_identity(df: pd.DataFrame):
    imo_counts = (
        df.loc[df["imo_number"].notna(), "imo_number"]
        .value_counts()
    )

    mmsi_counts = (
        df.loc[df["mmsi"].notna(), "mmsi"]
        .value_counts()
    )

    classifications = []

    for _, row in df.iterrows():
        imo = row["imo_number"]
        mmsi = row["mmsi"]

        duplicate_imo = (
            imo is not None
            and imo_counts.get(imo, 0) > 1
        )

        duplicate_mmsi = (
            mmsi is not None
            and mmsi_counts.get(mmsi, 0) > 1
        )

        if duplicate_imo or duplicate_mmsi:
            classification = "AMBIGUOUS_IDENTITY"
        elif imo is not None or mmsi is not None:
            classification = "INGESTABLE"
        else:
            classification = "REFERENCE_ONLY"

        classifications.append(classification)

    return classifications, imo_counts, mmsi_counts


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    source = load_source()

    normalized, stats = normalize(source)

    (
        classifications,
        imo_counts,
        mmsi_counts,
    ) = classify_identity(normalized)

    normalized["identity_classification"] = classifications

    normalized.to_csv(
        NORMALIZED_OUTPUT,
        index=False,
        na_rep="",
    )

    ambiguous = normalized[
        normalized["identity_classification"] == "AMBIGUOUS_IDENTITY"
    ].copy()

    ambiguous.to_csv(
        AMBIGUOUS_OUTPUT,
        index=False,
        na_rep="",
    )

    classification_counts = (
        normalized["identity_classification"]
        .value_counts()
        .to_dict()
    )

    report = {
        "source": "MarineVessels",
        "source_file": str(INPUT.relative_to(ROOT)),
        "source_rows": len(source),
        "normalized_rows": len(normalized),
        "quality": stats,
        "identity": {
            "unique_imo_values": int(len(imo_counts)),
            "duplicate_imo_values": int((imo_counts > 1).sum()),
            "duplicate_imo_rows": int(
                (imo_counts[imo_counts > 1] - 1).sum()
            ),
            "unique_mmsi_values": int(len(mmsi_counts)),
            "duplicate_mmsi_values": int((mmsi_counts > 1).sum()),
            "duplicate_mmsi_rows": int(
                (mmsi_counts[mmsi_counts > 1] - 1).sum()
            ),
            "classification_counts": classification_counts,
        },
        "policy": {
            "mode": "READ_ONLY",
            "supabase_writes": False,
            "missing_values": "preserved_as_null",
            "bad_fields": "nullified_individually",
            "duplicate_identity": "excluded_from_production_ingestion",
            "reference_only": "retained_in_normalized_dataset",
            "provenance": "PUBLIC_PROXY",
            "dimension_limits": {
                "max_draft_m": 30.0,
                "max_loa_m": 500.0,
                "max_beam_m": 80.0,
            },
        },
        "outputs": {
            "normalized": str(NORMALIZED_OUTPUT.relative_to(ROOT)),
            "ambiguous_identity": str(
                AMBIGUOUS_OUTPUT.relative_to(ROOT)
            ),
        },
    }

    REPORT_OUTPUT.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print("MarineVessels normalization complete.")
    print(f"Source rows:          {len(source)}")
    print(f"Normalized rows:      {len(normalized)}")
    print()
    print("--- FIELD QUALITY ---")
    print(f"Invalid IMO:          {stats['invalid_imo']}")
    print(f"Invalid MMSI:         {stats['invalid_mmsi']}")
    print(f"Invalid draught:      {stats['invalid_draught']}")
    print(f"Invalid length:       {stats['invalid_length']}")
    print(f"Invalid beam:         {stats['invalid_beam']}")
    print()
    print("--- IDENTITY ---")
    print(
        f"Unique IMO values:    {len(imo_counts)}"
    )
    print(
        f"Duplicate IMO values: {(imo_counts > 1).sum()}"
    )
    print(
        f"Unique MMSI values:   {len(mmsi_counts)}"
    )
    print(
        f"Duplicate MMSI:       {(mmsi_counts > 1).sum()}"
    )
    print()
    print("--- CLASSIFICATION ---")
    for key, value in classification_counts.items():
        print(f"{key:20} {value}")
    print()
    print(f"Normalized CSV:       {NORMALIZED_OUTPUT}")
    print(f"Ambiguous CSV:        {AMBIGUOUS_OUTPUT}")
    print(f"Validation report:    {REPORT_OUTPUT}")
    print()
    print("SUPABASE WRITES:      NONE")


if __name__ == "__main__":
    main()