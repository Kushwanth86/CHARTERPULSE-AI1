#!/usr/bin/env python3
"""One-shot/cron-friendly, server-side Baltic Exchange feed importer.

Required environment variables:
  BALTIC_EXCHANGE_API_KEY
  BALTIC_EXCHANGE_FEED_ID
  BALTIC_EXCHANGE_ROUTE_MAP_JSON
  SUPABASE_URL
  SUPABASE_SECRET_KEY

Use only with Baltic Exchange permissions/licensing that cover automated
retrieval, database storage, derived forecasts, and the intended display use.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

# Allow direct invocation from the repository root: python scripts/import_baltic_exchange.py
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from services.api.app.integrations.baltic_exchange import (  # noqa: E402
    BalticExchangeClient,
    load_route_mapping,
    parse_feed_observations,
)
from services.api.app.config.settings import get_settings  # noqa: E402
from services.api.app.repositories.supabase_client import (  # noqa: E402
    get_supabase_admin_client,
)


def _marker_key(marker: Any) -> str:
    return json.dumps(marker, sort_keys=True, separators=(",", ":"), default=str)


def _load_state(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def _upsert_observations(observations: list[dict[str, Any]]) -> tuple[int, int]:
    """Insert observations once, using provider code + date as a stable key.

    The table may not enforce uniqueness on source_reference yet, so this
    checks for an existing record before insert. Run only one importer process
    per feed at a time.
    """
    client = get_supabase_admin_client()
    inserted = 0
    existing_count = 0
    for observation in observations:
        reference = observation["source_reference"]
        existing = (
            client.table("market_observations")
            .select("id")
            .eq("source_reference", reference)
            .limit(1)
            .execute()
        )
        if existing.data:
            existing_count += 1
            continue
        response = client.table("market_observations").insert(observation).execute()
        if not response.data:
            raise RuntimeError(
                f"Supabase did not confirm insert for {reference}; rerun safely after checking the database."
            )
        inserted += 1
    return inserted, existing_count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-date", help="Optional lower bound, YYYY-MM-DD")
    parser.add_argument("--to-date", help="Optional inclusive upper bound, YYYY-MM-DD")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Fetch the feed even when latestDatumChangeOn matches the previous successful run.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and validate data but do not write to Supabase or update sync state.",
    )
    args = parser.parse_args()

    settings = get_settings()
    raw_route_map = (
        os.getenv("BALTIC_EXCHANGE_ROUTE_MAP_JSON")
        or settings.baltic_exchange_route_map_json
        or ""
    ).strip()
    if not raw_route_map:
        print("Missing BALTIC_EXCHANGE_ROUTE_MAP_JSON; no data was requested or imported.", file=sys.stderr)
        return 2

    try:
        route_mapping = load_route_mapping(raw_route_map)
        client = BalticExchangeClient()
        marker = client.latest_data_change()
    except (ValueError, RuntimeError) as exc:
        print(f"Baltic Exchange setup/check failed: {exc}", file=sys.stderr)
        return 2

    default_state = Path.home() / ".charterpulse" / "baltic_exchange_sync_state.json"
    state_path = Path(
        os.getenv("BALTIC_EXCHANGE_STATE_FILE")
        or settings.baltic_exchange_state_file
        or str(default_state)
    ).expanduser()
    state = _load_state(state_path)
    marker_key = _marker_key(marker)
    same_marker = (
        state.get("feed_id") == client.feed_identifier
        and state.get("api_version") == client.api_version
        and state.get("latest_data_change_key") == marker_key
    )
    if same_marker and not args.force:
        print("Baltic feed has not changed since the last successful import; no data request was made.")
        return 0

    try:
        payload = client.get_feed_data(from_date=args.from_date, to_date=args.to_date)
        batch = parse_feed_observations(payload, route_mapping)
    except (ValueError, RuntimeError) as exc:
        print(f"Baltic Exchange fetch/validation failed: {exc}", file=sys.stderr)
        return 2

    observations = batch["observations"]
    print(
        f"Validated observations: {len(observations)}; "
        f"skipped: {json.dumps(batch['skipped'], sort_keys=True)}"
    )
    if not observations:
        print(
            "No observations were eligible for import. Check route mappings, source units, and feed contents. "
            "Sync state was not advanced.",
            file=sys.stderr,
        )
        return 3
    if args.dry_run:
        print("Dry run only: no Supabase writes were made and sync state was not updated.")
        return 0

    try:
        inserted, existing_count = _upsert_observations(observations)
    except Exception as exc:
        # Avoid outputting request/client objects or any secret-bearing values.
        print(f"Supabase import failed: {type(exc).__name__}. Sync state was not advanced.", file=sys.stderr)
        return 4

    _write_state(
        state_path,
        {
            "feed_id": client.feed_identifier,
            "api_version": client.api_version,
            "latest_data_change_key": marker_key,
        },
    )
    print(
        f"Import complete. Inserted {inserted} observations; "
        f"skipped {existing_count} previously imported observations."
    )
    print(f"Sync state saved to {state_path}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
