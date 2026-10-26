from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from services.api.app.schemas.forecasts import FreightForecastRequest
from services.api.app.services.forecast_service import ForecastService


ORIGIN = UUID("00000000-0000-4000-8000-000000000001")
DESTINATION = UUID("00000000-0000-4000-8000-000000000002")


def observation(
    observed_at: str,
    value: float,
    *,
    provenance: str = "REAL",
    unit: str = "USD/MT",
    metric: str = "OCEAN_FREIGHT",
    vessel_class: str | None = "Panamax",
) -> dict:
    return {
        "market_type": "FREIGHT",
        "metric": metric,
        "value": value,
        "unit": unit,
        "currency": "USD",
        "origin_location_id": str(ORIGIN),
        "destination_location_id": str(DESTINATION),
        "vessel_class": vessel_class,
        "observed_at": observed_at,
        "source": "TEST_SOURCE",
        "source_reference": "TEST_FIXTURE",
        "provenance": provenance,
    }


class FakeMarketRepository:
    def __init__(self, rows: list[dict]):
        self.rows = rows
        self.last_query = None

    def list(self, **kwargs):
        self.last_query = kwargs
        rows = self.rows
        if kwargs.get("origin_location_id"):
            rows = [
                row for row in rows
                if row.get("origin_location_id") == str(kwargs["origin_location_id"])
            ]
        if kwargs.get("destination_location_id"):
            rows = [
                row for row in rows
                if row.get("destination_location_id") == str(kwargs["destination_location_id"])
            ]
        if kwargs.get("vessel_class"):
            rows = [
                row for row in rows
                if str(row.get("vessel_class") or "").casefold()
                == kwargs["vessel_class"].strip().casefold()
            ]
        if kwargs.get("metric"):
            rows = [row for row in rows if row.get("metric") == kwargs["metric"]]
        return rows[:kwargs.get("limit", 500)]


class FakeForecastRepository:
    def __init__(self, forecasts=None):
        self.forecasts = list(forecasts or [])
        self.created = []

    def create(self, payload):
        saved = {
            **payload,
            "id": "00000000-0000-4000-8000-000000000111",
            "generated_at": payload.get("generated_at") or datetime.now(timezone.utc).isoformat(),
        }
        self.created.append(saved)
        self.forecasts.insert(0, saved)
        return saved

    def list(self, **kwargs):
        rows = list(self.forecasts)
        if kwargs.get("origin_location_id"):
            rows = [
                row for row in rows
                if row.get("origin_location_id") == str(kwargs["origin_location_id"])
            ]
        if kwargs.get("destination_location_id"):
            rows = [
                row for row in rows
                if row.get("destination_location_id") == str(kwargs["destination_location_id"])
            ]
        if kwargs.get("vessel_class"):
            rows = [
                row for row in rows
                if str(row.get("vessel_class") or "").casefold()
                == kwargs["vessel_class"].strip().casefold()
            ]
        return rows[:kwargs.get("limit", 100)]


def route_request(**overrides) -> FreightForecastRequest:
    values = {
        "origin_location_id": ORIGIN,
        "destination_location_id": DESTINATION,
        "vessel_class": "Panamax",
        "forecast_horizon_days": 7,
        "metric": "freight_rate",
        "unit": "USD/MT",
        "currency": "USD",
    }
    values.update(overrides)
    return FreightForecastRequest(**values)


def service_with_rows(rows: list[dict]) -> ForecastService:
    service = ForecastService()
    service.market_repository = FakeMarketRepository(rows)
    service.forecast_repository = FakeForecastRepository()
    return service


def test_route_forecast_uses_only_real_or_public_proxy_matching_unit_and_class():
    rows = [
        observation("2026-10-20T00:00:00+00:00", 20.0),
        observation("2026-10-21T00:00:00+00:00", 21.0, provenance="PUBLIC_PROXY"),
        observation("2026-10-22T00:00:00+00:00", 22.0),
        observation("2026-10-23T00:00:00+00:00", 999.0, provenance="SIMULATED"),
        observation("2026-10-24T00:00:00+00:00", 888.0, unit="USD_per_40ft_container"),
        observation("2026-10-25T00:00:00+00:00", 777.0, vessel_class="Capesize"),
    ]
    service = service_with_rows(rows)

    result = service.generate(route_request())

    assert result["unit"] == "USD/MT"
    assert result["metadata"]["route_scoped"] is True
    assert result["metadata"]["input_provenance"] == "MARKET_OBSERVATION"
    assert result["metadata"]["observation_count"] == 3
    assert result["metadata"]["distinct_observation_dates"] == 3
    assert result["metadata"]["source_provenances"] == ["PUBLIC_PROXY", "REAL"]
    assert 999.0 not in [
        service.market_repository.rows[index]["value"]
        for index in range(3)
    ]


def test_default_metric_alias_matches_ocean_freight_observations():
    service = service_with_rows([
        observation("2026-10-20T00:00:00+00:00", 20.0),
        observation("2026-10-21T00:00:00+00:00", 21.0),
        observation("2026-10-22T00:00:00+00:00", 22.0),
    ])

    result = service.generate(route_request(metric="freight_rate"))

    assert result["metadata"]["observation_count"] == 3
    assert service.market_repository.last_query["metric"] is None


def test_no_static_fallback_for_missing_or_simulated_route_observations():
    service = service_with_rows([
        observation("2026-10-20T00:00:00+00:00", 28.4, provenance="SIMULATED"),
        observation("2026-10-21T00:00:00+00:00", 30.1, provenance="SIMULATED"),
        observation("2026-10-22T00:00:00+00:00", 31.5, provenance="SIMULATED"),
    ])

    with pytest.raises(ValueError, match="No eligible non-simulated market observations"):
        service.generate(route_request())

    assert service.forecast_repository.created == []


def test_route_forecast_requires_three_distinct_observation_dates():
    same_date = [
        observation("2026-10-20T00:00:00+00:00", 20.0),
        observation("2026-10-20T12:00:00+00:00", 21.0),
        observation("2026-10-20T18:00:00+00:00", 22.0),
    ]
    service = service_with_rows(same_date)

    with pytest.raises(ValueError, match="three eligible observations from distinct dates"):
        service.generate(route_request())


def test_partial_route_request_cannot_generate_unscoped_forecast():
    service = service_with_rows([
        observation("2026-10-20T00:00:00+00:00", 20.0),
        observation("2026-10-21T00:00:00+00:00", 21.0),
        observation("2026-10-22T00:00:00+00:00", 22.0),
    ])

    with pytest.raises(ValueError, match="requires both origin and destination"):
        service.generate(route_request(destination_location_id=None))


def test_forecast_listing_excludes_legacy_proxy_reference_rows():
    legacy = {
        "id": "legacy-forecast",
        "origin_location_id": str(ORIGIN),
        "destination_location_id": str(DESTINATION),
        "vessel_class": "Panamax",
        "p10": 32.0,
        "p50": 34.0,
        "p90": 36.0,
        "unit": "USD/MT",
        "provenance": "PUBLIC_PROXY_REFERENCE",
        "generated_at": "2026-10-26T10:00:00+00:00",
        "metadata": {
            "observation_count": 3,
            "observed_median": 30.1,
        },
    }
    service = service_with_rows([])
    service.forecast_repository = FakeForecastRepository([legacy])

    assert service.list(ORIGIN, DESTINATION, "Panamax") == []
