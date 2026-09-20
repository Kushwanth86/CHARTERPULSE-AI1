from __future__ import annotations

import json
from pathlib import Path

from services.api.app.repositories.supabase_client import get_supabase_client


BASE = Path(__file__).resolve().parents[2]
WPI_DIR = BASE / "data" / "processed" / "wpi"

WPI_FILE = WPI_DIR / "wpi_normalized.jsonl"
MATCHING_REPORT = WPI_DIR / "wpi_matching_report.json"
OUTPUT_JSONL = WPI_DIR / "wpi_enrichment_preview.jsonl"
OUTPUT_REPORT = WPI_DIR / "wpi_enrichment_report.json"

PAGE_SIZE = 1000


def normalize_unlocode(value):
    if not value:
        return None

    value = str(value).strip().upper().replace(" ", "")

    if len(value) != 5:
        return None

    return value


def load_jsonl(path):
    records = []

    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    return records


def fetch_table(client, table_name, select_fields):
    rows = []
    offset = 0

    while True:
        response = (
            client.table(table_name)
            .select(select_fields)
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
        )

        batch = response.data or []
        rows.extend(batch)

        if len(batch) < PAGE_SIZE:
            break

        offset += PAGE_SIZE

    return rows


def normalize_list(value):
    if not value:
        return None

    if isinstance(value, str):
        values = [value]
    else:
        values = value

    normalized = sorted(
        {
            str(item).strip().upper()
            for item in values
            if str(item).strip()
        }
    )

    return normalized or None


def classify(field, current, candidate, current_provenance=None):
    if candidate is None:
        return "NO_WPI_VALUE"

    if current is None:
        return "CANDIDATE_NEW"

    if field in {"max_loa_m", "max_beam_m", "max_draft_m"}:
        try:
            if abs(float(current) - float(candidate)) <= 0.01:
                return "SAME"
        except (TypeError, ValueError):
            pass
    elif current == candidate:
        return "SAME"

    if current_provenance == "SIMULATED":
        return "REPLACE_SIMULATED"

    return "CONFLICT_REVIEW"

def action_for_classification(classification):
    if classification == "CANDIDATE_NEW":
        return "FILL_NULL"

    if classification == "REPLACE_SIMULATED":
        return "REPLACE_SIMULATED"

    if classification == "CONFLICT_REVIEW":
        return "CONFLICT_REVIEW"

    return None


def main():
    if not WPI_FILE.exists():
        raise FileNotFoundError(f"Missing WPI file: {WPI_FILE}")

    if not MATCHING_REPORT.exists():
        raise FileNotFoundError(
            f"Missing WPI matching report: {MATCHING_REPORT}"
        )

    wpi_records = load_jsonl(WPI_FILE)

    with MATCHING_REPORT.open("r", encoding="utf-8") as handle:
        matching_report = json.load(handle)

    duplicate_unlocodes = {
        normalize_unlocode(value)
        for value in matching_report.get("duplicate_unlocode_values", [])
    }
    duplicate_unlocodes.discard(None)

    client = get_supabase_client()

    ports = fetch_table(
        client,
        "ports",
        "id,name,unlocode,rail_connected,source,source_url,observed_at",
    )

    constraints = fetch_table(
        client,
        "port_constraints",
        (
            "id,port_id,max_loa_m,max_beam_m,max_draft_m,"
            "cargo_handling_types,loading_available,discharge_available,"
            "source,source_reference,provenance,observed_at"
        ),
    )

    ports_by_unlocode = {}
    for port in ports:
        unlocode = normalize_unlocode(port.get("unlocode"))
        if unlocode:
            ports_by_unlocode.setdefault(unlocode, []).append(port)

    constraints_by_port_id = {
        str(row["port_id"]): row
        for row in constraints
        if row.get("port_id")
    }

    preview_rows = []

    summary = {
        "wpi_records": len(wpi_records),
        "duplicate_wpi_records_excluded": 0,
        "matched_ports": 0,
        "unmatched_wpi_records": 0,
        "duplicate_port_matches": 0,
        "candidate_new": 0,
        "same": 0,
        "replace_simulated": 0,
        "conflict_review": 0,
        "no_wpi_value": 0,
        "fields": {},
    }

    field_names = [
        "max_loa_m",
        "max_beam_m",
        "max_draft_m",
        "rail_connected",
        "cargo_handling_types",
    ]

    for field in field_names:
        summary["fields"][field] = {
            "candidate_new": 0,
            "same": 0,
            "replace_simulated": 0,
            "conflict_review": 0,
            "no_wpi_value": 0,
        }

    for wpi in wpi_records:
        unlocode = normalize_unlocode(wpi.get("unlocode"))

        if not unlocode:
            summary["unmatched_wpi_records"] += 1
            continue

        if unlocode in duplicate_unlocodes:
            summary["duplicate_wpi_records_excluded"] += 1
            continue

        matches = ports_by_unlocode.get(unlocode, [])

        if not matches:
            summary["unmatched_wpi_records"] += 1
            continue

        if len(matches) > 1:
            summary["duplicate_port_matches"] += 1
            continue

        port = matches[0]
        summary["matched_ports"] += 1

        constraint = constraints_by_port_id.get(str(port["id"]), {})
        constraint_provenance = constraint.get("provenance")
        constraint_source = constraint.get("source")

        current_cargo = normalize_list(
            constraint.get("cargo_handling_types")
        )
        wpi_cargo = normalize_list(wpi.get("cargo_handling_types"))

        fields = {
            "max_loa_m": {
                "current": constraint.get("max_loa_m"),
                "wpi": wpi.get("max_loa_m"),
                "current_provenance": constraint_provenance,
            },
            "max_beam_m": {
                "current": constraint.get("max_beam_m"),
                "wpi": wpi.get("max_beam_m"),
                "current_provenance": constraint_provenance,
            },
            "max_draft_m": {
                "current": constraint.get("max_draft_m"),
                "wpi": wpi.get("max_draft_m"),
                "current_provenance": constraint_provenance,
            },
            "rail_connected": {
                "current": port.get("rail_connected"),
                "wpi": wpi.get("rail_connected"),
                "current_provenance": None,
            },
            "cargo_handling_types": {
                "current": current_cargo,
                "wpi": wpi_cargo,
                "current_provenance": constraint_provenance,
            },
        }

        classifications = {}
        actions = {}

        for field, values in fields.items():
            status = classify(
                field,
                values["current"],
                values["wpi"],
                values["current_provenance"],
            )
            
            classifications[field] = status
            actions[field] = action_for_classification(status)

            summary["fields"][field][status.lower()] += 1

            if status == "CANDIDATE_NEW":
                summary["candidate_new"] += 1
            elif status == "SAME":
                summary["same"] += 1
            elif status == "REPLACE_SIMULATED":
                summary["replace_simulated"] += 1
            elif status == "CONFLICT_REVIEW":
                summary["conflict_review"] += 1
            elif status == "NO_WPI_VALUE":
                summary["no_wpi_value"] += 1

        preview_rows.append(
            {
                "port_id": port["id"],
                "port_name": port.get("name"),
                "unlocode": unlocode,
                "constraint_provenance": constraint_provenance,
                "constraint_source": constraint_source,
                "fields": fields,
                "classification": classifications,
                "actions": actions,
                "wpi_source": wpi.get("source"),
                "wpi_source_url": wpi.get("source_url"),
                "wpi_provenance": wpi.get("provenance"),
                "wpi_observed_at": wpi.get("observed_at"),
            }
        )

    with OUTPUT_JSONL.open("w", encoding="utf-8") as handle:
        for row in preview_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    summary["preview_rows"] = len(preview_rows)

    with OUTPUT_REPORT.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, ensure_ascii=False)

    print("WPI enrichment preview complete.")
    print(f"WPI records: {summary['wpi_records']}")
    print(
        "Duplicate WPI records excluded: "
        f"{summary['duplicate_wpi_records_excluded']}"
    )
    print(f"Matched ports: {summary['matched_ports']}")
    print(f"Unmatched WPI records: {summary['unmatched_wpi_records']}")
    print(f"Duplicate port matches: {summary['duplicate_port_matches']}")
    print("\nActions:")
    print(f"  FILL_NULL:          {summary['candidate_new']}")
    print(f"  REPLACE_SIMULATED:  {summary['replace_simulated']}")
    print(f"  CONFLICT_REVIEW:    {summary['conflict_review']}")
    print(f"  SAME:               {summary['same']}")
    print(f"  NO_WPI_VALUE:       {summary['no_wpi_value']}")

    print("\nField results:")
    for field, values in summary["fields"].items():
        print(f"  {field}:")
        print(f"    CANDIDATE_NEW:     {values['candidate_new']}")
        print(f"    SAME:              {values['same']}")
        print(f"    REPLACE_SIMULATED: {values['replace_simulated']}")
        print(f"    CONFLICT_REVIEW:   {values['conflict_review']}")
        print(f"    NO_WPI_VALUE:      {values['no_wpi_value']}")

    print(f"\nPreview: {OUTPUT_JSONL}")
    print(f"Report: {OUTPUT_REPORT}")


if __name__ == "__main__":
    main()
