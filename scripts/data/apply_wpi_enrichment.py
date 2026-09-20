from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from services.api.app.repositories.supabase_client import get_supabase_admin_client


BASE = Path(__file__).resolve().parents[2]
WPI_DIR = BASE / "data" / "processed" / "wpi"
PREVIEW_PATH = WPI_DIR / "wpi_enrichment_preview.jsonl"
REPORT_PATH = WPI_DIR / "wpi_apply_report.json"

ALLOWED_ACTIONS = {"FILL_NULL", "REPLACE_SIMULATED"}
BLOCKED_CLASSIFICATIONS = {"CONFLICT_REVIEW"}
SUPPORTED_FIELDS = {
    "max_loa_m",
    "max_beam_m",
    "max_draft_m",
    "rail_connected",
    "cargo_handling_types",
}
RPC_NAME = "apply_wpi_enrichment"


def load_preview() -> list[dict]:
    if not PREVIEW_PATH.exists():
        raise FileNotFoundError(f"Missing WPI preview: {PREVIEW_PATH}")

    with PREVIEW_PATH.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def build_plan(rows: list[dict]) -> list[dict]:
    plan: list[dict] = []

    for row in rows:
        actions: list[dict] = []

        for field in SUPPORTED_FIELDS:
            classification = row.get("classification", {}).get(field)
            action = row.get("actions", {}).get(field)

            if classification in BLOCKED_CLASSIFICATIONS:
                raise RuntimeError(
                    f"WPI apply blocked by CONFLICT_REVIEW: "
                    f"{row.get('port_name')} {row.get('unlocode')} {field}"
                )

            if classification in {"SAME", "NO_WPI_VALUE", None}:
                continue

            if classification == "CANDIDATE_NEW":
                expected_action = "FILL_NULL"
            elif classification == "REPLACE_SIMULATED":
                expected_action = "REPLACE_SIMULATED"
            else:
                raise RuntimeError(
                    f"Unsupported WPI classification {classification!r} for "
                    f"{row.get('port_name')} {row.get('unlocode')} {field}"
                )

            if action not in (None, expected_action):
                raise RuntimeError(
                    f"Preview action mismatch for {row.get('port_name')} "
                    f"{field}: classification={classification}, action={action}"
                )

            if field not in SUPPORTED_FIELDS:
                raise RuntimeError(f"Unsupported WPI field: {field}")

            value = row["fields"][field]
            if value.get("wpi") is None:
                raise RuntimeError(
                    f"WPI action has null candidate for {row.get('port_name')} {field}"
                )

            actions.append(
                {
                    "field": field,
                    "action": expected_action,
                    "current": value.get("current"),
                    "wpi": value.get("wpi"),
                }
            )

        if actions:
            plan.append(
                {
                    "port_id": row["port_id"],
                    "port_name": row.get("port_name"),
                    "unlocode": row.get("unlocode"),
                    "actions": actions,
                    "wpi_source": row.get("wpi_source"),
                    "wpi_source_url": row.get("wpi_source_url"),
                    "wpi_provenance": row.get("wpi_provenance"),
                }
            )

    return plan


def validate_plan(plan: list[dict]) -> None:
    seen_ports: set[str] = set()

    for item in plan:
        port_id = item.get("port_id")
        if not port_id:
            raise RuntimeError("WPI apply plan contains a row without port_id")

        if port_id in seen_ports:
            raise RuntimeError(f"Duplicate port in WPI apply plan: {port_id}")
        seen_ports.add(port_id)

        for action in item["actions"]:
            if action["action"] not in ALLOWED_ACTIONS:
                raise RuntimeError(
                    f"Unsupported WPI apply action: {action['action']}"
                )
            if action["field"] not in SUPPORTED_FIELDS:
                raise RuntimeError(
                    f"Unsupported WPI apply field: {action['field']}"
                )


def summarize(plan: list[dict]) -> dict:
    summary = {
        "ports_with_actions": len(plan),
        "fill_null": 0,
        "replace_simulated": 0,
        "field_actions": {field: 0 for field in sorted(SUPPORTED_FIELDS)},
    }

    for item in plan:
        for action in item["actions"]:
            summary[action["action"].lower()] += 1
            summary["field_actions"][action["field"]] += 1

    return summary


def write_report(
    plan: list[dict],
    summary: dict,
    *,
    dry_run: bool,
    rpc_result: dict | None = None,
) -> None:
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
        "source": "NGA World Port Index",
        "source_url": (
            "https://fgmod.nga.mil/nauticalpubs-feature/"
            "rest/services/WPI/WPI_Viewer/FeatureServer/0"
        ),
        "provenance": "REAL",
        "summary": summary,
        "rpc_result": rpc_result,
        "plan": plan,
    }

    REPORT_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def print_plan(summary: dict) -> None:
    print("WPI enrichment apply plan")
    print("==========================")
    print(f"Ports with actions: {summary['ports_with_actions']}")
    print(f"FILL_NULL: {summary['fill_null']}")
    print(f"REPLACE_SIMULATED: {summary['replace_simulated']}")
    print("\nField actions:")
    for field, count in summary["field_actions"].items():
        print(f"  {field}: {count}")


def apply_plan(plan: list[dict]) -> dict:
    client = get_supabase_admin_client()

    response = client.rpc(RPC_NAME, {"p_plan": plan}).execute()
    if not response.data:
        raise RuntimeError("WPI enrichment RPC returned no result")

    if isinstance(response.data, list):
        return response.data[0]
    return response.data


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply approved NGA WPI enrichment through a transactional RPC."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Commit the WPI enrichment transaction. Default is dry-run only.",
    )
    args = parser.parse_args()

    rows = load_preview()
    plan = build_plan(rows)
    validate_plan(plan)
    summary = summarize(plan)
    print_plan(summary)

    if not args.apply:
        write_report(plan, summary, dry_run=True)
        print("\nNO DATABASE WRITES PERFORMED.")
        print(f"Dry-run report: {REPORT_PATH}")
        return 0

    print("\nApplying WPI enrichment through transactional RPC...")
    rpc_result = apply_plan(plan)
    write_report(plan, summary, dry_run=False, rpc_result=rpc_result)

    print("WPI enrichment committed.")
    print(f"RPC result: {json.dumps(rpc_result, sort_keys=True)}")
    print(f"Apply report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
