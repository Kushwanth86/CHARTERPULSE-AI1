from __future__ import annotations

import csv
from datetime import datetime, timezone

import pytest

from scripts.data.ingest_freight_observations import (
    build_payloads,
    parse_csv,
    prepare_insert_plan,
    resolve_locations,
)


def row(**overrides):
    result = {
        "origin_unlocode": "auabp",
        "destination_unlocode": "inach",
        "vessel_class": "Panamax",
        "market_type": "DRY_BULK_FREIGHT",
        "metric": "freight_rate",
        "value": "29.75",
        "unit": "USD/MT",
        "currency": "USD",
        "observed_at": "2026-10-20T12:00:00Z",
        "retrieved_at": "2026-10-25T15:00:00+05:30",
        "source": "Licensed Freight Provider",
        "source_record_id": "quote-123",
        "source_reference": "https://provider.example/quote/quote-123",
        "provenance": "REAL",
    }
    result.update(overrides)
    return result


def write_csv(tmp_path, rows):
    path = tmp_path / "observations.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def test_parse_csv_normalizes_route_timestamps_and_source_identity(tmp_path):
    path = write_csv(tmp_path, [row()])

    result = parse_csv(path)

    assert len(result) == 1
    assert result[0]["origin_unlocode"] == "AUABP"
    assert result[0]["destination_unlocode"] == "INACH"
    assert result[0]["value"] == 29.75
    assert result[0]["metric"] == "freight_rate"
    assert result[0]["unit"] == "USD/MT"
    assert result[0]["observed_at"] == "2026-10-20T12:00:00Z"
    assert result[0]["retrieved_at"] == "2026-10-25T09:30:00Z"
    assert result[0]["source_record_id"] == "quote-123"


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"provenance": "SIMULATED"}, "not accepted for production ingestion"),
        ({"provenance": "FORECAST"}, "not accepted for production ingestion"),
        ({"unit": "index points"}, "expected unit"),
        ({"unit": "USD/day"}, "expected unit"),
        ({"value": "0"}, "greater than zero"),
        ({"value": "nan"}, "finite and greater than zero"),
        ({"observed_at": "2026-10-20T12:00:00"}, "must include a timezone"),
        ({"retrieved_at": ""}, "retrieved_at is required"),
        ({"origin_unlocode": "AU"}, "invalid origin UN/LOCODE"),
        ({"source_record_id": ""}, "source_record_id is required"),
    ],
)
def test_parse_csv_rejects_unsafe_or_incompatible_observations(
    tmp_path, overrides, message
):
    path = write_csv(tmp_path, [row(**overrides)])

    with pytest.raises(ValueError, match=message):
        parse_csv(path)


def test_parse_csv_rejects_reused_source_identity_in_one_file(tmp_path):
    path = write_csv(
        tmp_path,
        [row(), row(value="31.00")],
    )

    with pytest.raises(ValueError, match="duplicate source_record_id"):
        parse_csv(path)


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows
        self.columns = None
        self.codes = None

    def select(self, columns):
        self.columns = columns
        return self

    def in_(self, column, values):
        assert column == "unlocode"
        self.codes = set(values)
        return self

    def execute(self):
        from types import SimpleNamespace

        return SimpleNamespace(
            data=[r for r in self.rows if r["unlocode"] in self.codes]
        )


class FakeClient:
    def __init__(self, rows):
        self.rows = rows
        self.query = FakeQuery(rows)

    def table(self, name):
        assert name == "locations"
        return self.query


def test_resolve_locations_uses_exact_unlocode_to_location_ids():
    client = FakeClient(
        [
            {"id": "origin-uuid", "unlocode": "AUABP", "name": "Abbot Point"},
            {"id": "destination-uuid", "unlocode": "INACH", "name": "Achra"},
        ]
    )

    result = resolve_locations(client, {"AUABP", "INACH"})

    assert result["AUABP"]["id"] == "origin-uuid"
    assert result["INACH"]["id"] == "destination-uuid"


def test_resolve_locations_does_not_substitute_nearby_ports():
    client = FakeClient(
        [{"id": "other", "unlocode": "AUXXX", "name": "Other Port"}]
    )

    with pytest.raises(ValueError, match="Do not substitute nearby ports"):
        resolve_locations(client, {"AUABP"})


def test_build_payloads_preserves_source_and_normalization_provenance():
    parsed = [{
        **row(),
        "origin_unlocode": "AUABP",
        "destination_unlocode": "INACH",
        "value": 29.75,
        "observed_at": "2026-10-20T12:00:00Z",
        "retrieved_at": "2026-10-25T09:30:00Z",
        "_row_number": 2,
    }]
    locations = {
        "AUABP": {"id": "origin-uuid", "name": "Abbot Point"},
        "INACH": {"id": "destination-uuid", "name": "Achra"},
    }

    result = build_payloads(parsed, locations, input_filename="/private/quotes.csv")

    assert result[0]["origin_location_id"] == "origin-uuid"
    assert result[0]["destination_location_id"] == "destination-uuid"
    assert result[0]["source_record_id"] == "quote-123"
    assert result[0]["metadata"]["input_filename"] == "quotes.csv"
    assert result[0]["metadata"]["route_identity"] == {
        "origin_unlocode": "AUABP",
        "destination_unlocode": "INACH",
    }


def test_prepare_insert_plan_skips_exact_replay():
    payload = {
        "origin_location_id": "origin",
        "destination_location_id": "destination",
        "vessel_class": "Panamax",
        "metric": "freight_rate",
        "observed_at": "2026-10-20T12:00:00Z",
        "source": "Licensed Freight Provider",
        "source_record_id": "quote-123",
        "value": 29.75,
        "unit": "USD/MT",
        "currency": "USD",
        "source_reference": "https://provider.example/quote/quote-123",
        "provenance": "REAL",
    }

    inserts, skipped = prepare_insert_plan([payload], [dict(payload)])

    assert inserts == []
    assert skipped == 1


def test_prepare_insert_plan_rejects_silent_correction_of_old_observation():
    payload = {
        "origin_location_id": "origin",
        "destination_location_id": "destination",
        "vessel_class": "Panamax",
        "metric": "freight_rate",
        "observed_at": "2026-10-20T12:00:00Z",
        "source": "Licensed Freight Provider",
        "source_record_id": "quote-123",
        "value": 29.75,
        "unit": "USD/MT",
        "currency": "USD",
        "source_reference": "https://provider.example/quote/quote-123",
        "provenance": "REAL",
    }

    with pytest.raises(ValueError, match="Do not overwrite historical observations silently"):
        prepare_insert_plan(
            [dict(payload, value=30.00)],
            [dict(payload)],
        )


def test_ingestion_provenance_fields_are_readable_but_not_required_on_create():
    from services.api.app.schemas.market import (
        MarketObservationCreate,
        MarketObservationResponse,
    )

    base = {
        "market_type": "DRY_BULK_FREIGHT",
        "metric": "freight_rate",
        "origin_location_id": "00000000-0000-4000-8000-000000000001",
        "destination_location_id": "00000000-0000-4000-8000-000000000002",
        "vessel_class": "Panamax",
        "value": 29.75,
        "unit": "USD/MT",
        "currency": "USD",
        "observed_at": "2026-10-20T12:00:00Z",
        "source": "Licensed Freight Provider",
        "source_reference": "https://provider.example/quote/quote-123",
        "provenance": "REAL",
    }
    create = MarketObservationCreate(**base)
    dumped = create.model_dump(mode="json")

    assert "source_record_id" not in dumped
    assert "retrieved_at" not in dumped
    assert "ingested_at" not in dumped
    assert "metadata" not in dumped

    response = MarketObservationResponse(
        **base,
        id="00000000-0000-4000-8000-000000000003",
        created_at="2026-10-25T15:00:00Z",
        source_record_id="quote-123",
        retrieved_at="2026-10-25T09:30:00Z",
        ingested_at="2026-10-25T15:00:01Z",
        metadata={"schema_version": "1"},
    )
    assert response.source_record_id == "quote-123"
    assert response.retrieved_at is not None
    assert response.ingested_at is not None
    assert response.metadata == {"schema_version": "1"}


def test_parse_csv_rejects_reusing_source_record_id_for_another_route(tmp_path):
    path = write_csv(
        tmp_path,
        [
            row(),
            row(destination_unlocode="INXXX", observed_at="2026-10-21T12:00:00Z"),
        ],
    )

    with pytest.raises(ValueError, match="duplicate source_record_id"):
        parse_csv(path)


def test_parse_csv_rejects_retrieval_timestamp_before_observation(tmp_path):
    path = write_csv(
        tmp_path,
        [row(retrieved_at="2026-10-19T12:00:00Z")],
    )

    with pytest.raises(ValueError, match="retrieved_at cannot precede observed_at"):
        parse_csv(path)


def test_prepare_insert_plan_rejects_source_id_reused_for_another_route():
    payload = {
        "origin_location_id": "origin",
        "destination_location_id": "destination",
        "vessel_class": "Panamax",
        "market_type": "DRY_BULK_FREIGHT",
        "metric": "freight_rate",
        "observed_at": "2026-10-20T12:00:00Z",
        "source": "Licensed Freight Provider",
        "source_record_id": "quote-123",
        "value": 29.75,
        "unit": "USD/MT",
        "currency": "USD",
        "source_reference": "https://provider.example/quote/quote-123",
        "provenance": "REAL",
    }

    changed_route = dict(payload, destination_location_id="different-destination")
    with pytest.raises(ValueError, match="Do not overwrite historical observations silently"):
        prepare_insert_plan([changed_route], [payload])
