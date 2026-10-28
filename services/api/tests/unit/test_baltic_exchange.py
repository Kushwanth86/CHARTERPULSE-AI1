from __future__ import annotations

import json
from urllib.error import HTTPError
from uuid import UUID

import pytest

from services.api.app.integrations.baltic_exchange import (
    BalticExchangeAPIError,
    BalticExchangeClient,
    load_route_mapping,
    parse_feed_observations,
)


ORIGIN = "00000000-0000-4000-8000-000000000001"
DESTINATION = "00000000-0000-4000-8000-000000000002"


def route_mapping():
    return {
        "C5": {
            "origin_location_id": ORIGIN,
            "destination_location_id": DESTINATION,
            "vessel_class": "Capesize",
        }
    }


def feed_payload():
    return [
        {
            "id": "C5",
            "shortCode": "C5",
            "shortDescription": "Capesize West Australia to Qingdao",
            "displayGroup": "Capesize",
            "datumUnit": "$/mt",
            "datumPrecision": 3,
            "data": [
                {"value": 12.34, "date": "2026-10-20"},
                {"value": "13.25", "date": "2026-10-21T00:00:00"},
            ],
        }
    ]


def test_feed_observations_are_normalized_with_explicit_route_and_provenance():
    batch = parse_feed_observations(feed_payload(), route_mapping())

    assert batch["skipped"] == {
        "unmapped_source": 0,
        "unsupported_unit": 0,
        "invalid_point": 0,
        "duplicate_point": 0,
    }
    assert len(batch["observations"]) == 2
    first = batch["observations"][0]
    assert first["market_type"] == "FREIGHT"
    assert first["metric"] == "OCEAN_FREIGHT"
    assert first["origin_location_id"] == ORIGIN
    assert first["destination_location_id"] == DESTINATION
    assert first["vessel_class"] == "Capesize"
    assert first["value"] == 12.34
    assert first["unit"] == "USD/MT"
    assert first["currency"] == "USD"
    assert first["provenance"] == "REAL"
    assert first["source_reference"] == "baltic-exchange:C5:2026-10-20"
    assert first["observed_at"].endswith("+00:00")


def test_unmapped_benchmark_is_skipped_instead_of_guessing_a_route():
    batch = parse_feed_observations(feed_payload(), {})

    assert batch["observations"] == []
    assert batch["skipped"]["unmapped_source"] == 1


def test_non_usd_per_metric_ton_units_are_rejected_not_converted():
    payload = feed_payload()
    payload[0]["datumUnit"] = "$/day"

    batch = parse_feed_observations(payload, route_mapping())

    assert batch["observations"] == []
    assert batch["skipped"]["unsupported_unit"] == 1


@pytest.mark.parametrize(
    "value, observed_date",
    [
        ("nan", "2026-10-20"),
        ("inf", "2026-10-20"),
        (0, "2026-10-20"),
        (-2, "2026-10-20"),
        (True, "2026-10-20"),
        (12.0, "not-a-date"),
    ],
)
def test_invalid_values_or_dates_are_skipped(value, observed_date):
    payload = feed_payload()
    payload[0]["data"] = [{"value": value, "date": observed_date}]

    batch = parse_feed_observations(payload, route_mapping())

    assert batch["observations"] == []
    assert batch["skipped"]["invalid_point"] == 1


def test_duplicate_source_date_is_deduplicated():
    payload = feed_payload()
    payload[0]["data"] = [
        {"value": 12.0, "date": "2026-10-20"},
        {"value": 12.5, "date": "2026-10-20T15:00:00Z"},
    ]

    batch = parse_feed_observations(payload, route_mapping())

    assert len(batch["observations"]) == 1
    assert batch["skipped"]["duplicate_point"] == 1


def test_route_mapping_requires_valid_distinct_location_ids_and_vessel_class():
    raw = json.dumps(
        {
            "C5": {
                "origin_location_id": ORIGIN,
                "destination_location_id": DESTINATION,
                "vessel_class": "Capesize",
            }
        }
    )
    result = load_route_mapping(raw)
    assert result["C5"]["origin_location_id"] == str(UUID(ORIGIN))

    invalid = json.dumps(
        {
            "C5": {
                "origin_location_id": ORIGIN,
                "destination_location_id": ORIGIN,
                "vessel_class": "Capesize",
            }
        }
    )
    with pytest.raises(ValueError, match="distinct"):
        load_route_mapping(invalid)


def test_client_uses_key_header_and_documented_feed_paths(monkeypatch):
    requests = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return b'"2026-10-26T12:00:00Z"'

    def fake_urlopen(request, timeout):
        requests.append((request, timeout))
        return Response()

    monkeypatch.setattr(
        "services.api.app.integrations.baltic_exchange.urlopen",
        fake_urlopen,
    )
    client = BalticExchangeClient(
        api_key="test-secret",
        feed_identifier="FDS123",
        api_version="v1.3",
    )

    marker = client.latest_data_change()

    assert marker == "2026-10-26T12:00:00Z"
    request, timeout = requests[0]
    assert request.full_url.endswith("/v1.3/feed/FDS123/latestDatumChangeOn")
    assert any(
        key.lower() == "x-apikey" and value == "test-secret"
        for key, value in request.header_items()
    )
    assert timeout == 20.0


def test_unauthorized_error_does_not_leak_api_key(monkeypatch):
    def fake_urlopen(request, timeout):
        raise HTTPError(request.full_url, 401, "Unauthorized", None, None)

    monkeypatch.setattr(
        "services.api.app.integrations.baltic_exchange.urlopen",
        fake_urlopen,
    )
    client = BalticExchangeClient(
        api_key="this-is-a-secret",
        feed_identifier="FDS123",
    )

    with pytest.raises(BalticExchangeAPIError) as exc:
        client.latest_data_change()

    assert "API key" in str(exc.value)
    assert "this-is-a-secret" not in str(exc.value)



def test_client_rejects_untrusted_base_url_before_sending_key():
    with pytest.raises(ValueError, match="official Baltic Exchange"):
        BalticExchangeClient(
            api_key="test-secret",
            feed_identifier="FDS123",
            base_url="https://example.invalid",
        )

def test_feed_data_adds_valid_inclusive_date_parameters(monkeypatch):
    seen = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return b"[]"

    def fake_urlopen(request, timeout):
        seen.append(request.full_url)
        return Response()

    monkeypatch.setattr(
        "services.api.app.integrations.baltic_exchange.urlopen",
        fake_urlopen,
    )
    client = BalticExchangeClient(
        api_key="test-secret",
        feed_identifier="FDS123",
    )

    assert client.get_feed_data("2026-10-01", "2026-10-31") == []
    assert seen[0].endswith("/data?from=2026-10-01&to=2026-10-31")
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        client.get_feed_data(from_date="01-10-2026")
