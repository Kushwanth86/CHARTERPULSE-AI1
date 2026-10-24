from datetime import datetime, timezone
from uuid import UUID

import pytest

from services.api.app.services import forecast_service


ORIGIN = UUID("00000000-0000-0000-0000-000000000001")
DESTINATION = UUID("00000000-0000-0000-0000-000000000002")


class FakeMarketRepository:
    def __init__(self, rows):
        self.rows = rows
        self.kwargs = None

    def list(self, **kwargs):
        self.kwargs = kwargs
        return self.rows


class FakeForecastRepository:
    pass


def observation(value, observed_at, provenance="REAL"):
    return {
        "metric": "OCEAN_FREIGHT",
        "value": value,
        "unit": "USD/MT",
        "currency": "USD",
        "origin_location_id": str(ORIGIN),
        "destination_location_id": str(DESTINATION),
        "vessel_class": "PANAMAX",
        "observed_at": observed_at,
        "provenance": provenance,
    }


def build_service(monkeypatch, rows):
    market = FakeMarketRepository(rows)
    monkeypatch.setattr(forecast_service, "MarketRepository", lambda: market)
    monkeypatch.setattr(forecast_service, "ForecastRepository", FakeForecastRepository)
    return forecast_service.ForecastService(), market


def test_monthly_forecast_requires_verified_route_and_class_observations(monkeypatch):
    service, _ = build_service(
        monkeypatch,
        [observation(30.0, "2026-09-01T00:00:00Z", provenance="SIMULATED")],
    )

    with pytest.raises(ValueError, match="No verified observations match"):
        service.monthly_forecast(ORIGIN, DESTINATION, "PANAMAX", months=3)


def test_monthly_forecast_returns_month_end_quantiles_and_scopes_market_query(monkeypatch):
    service, market = build_service(
        monkeypatch,
        [
            observation(28.0, "2026-08-01T00:00:00Z"),
            observation(29.0, "2026-08-08T00:00:00Z"),
            observation(31.0, "2026-08-15T00:00:00Z"),
        ],
    )

    result = service.monthly_forecast(ORIGIN, DESTINATION, "PANAMAX", months=3)

    assert [row["month"] for row in result] == ["2026-09", "2026-10", "2026-11"]
    assert all(row["p10"] <= row["p50"] <= row["p90"] for row in result)
    assert all(row["input_provenance"] == "VERIFIED_MATCHED_OBSERVATIONS" for row in result)
    assert [row["horizon_days"] for row in result] == sorted(row["horizon_days"] for row in result)
    assert market.kwargs["origin_location_id"] == ORIGIN
    assert market.kwargs["destination_location_id"] == DESTINATION
    assert market.kwargs["vessel_class"] == "PANAMAX"


def test_monthly_forecast_rejects_observations_for_another_route(monkeypatch):
    row = observation(30.0, "2026-09-01T00:00:00Z")
    row["origin_location_id"] = "00000000-0000-0000-0000-000000000099"
    service, _ = build_service(monkeypatch, [row])

    with pytest.raises(ValueError, match="No verified observations match"):
        service.monthly_forecast(ORIGIN, DESTINATION, "PANAMAX", months=1)
