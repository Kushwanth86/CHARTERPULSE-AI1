from __future__ import annotations

from uuid import UUID

import pytest
from pydantic import ValidationError

from services.api.app.decision import decision_engine
from services.api.app.decision.decision_engine import DecisionRequest
from services.api.app.services.forecast_evidence import assert_decision_eligible_forecast


ORIGIN = "00000000-0000-4000-8000-000000000001"
DESTINATION = "00000000-0000-4000-8000-000000000002"
CARGO_ID = UUID("00000000-0000-4000-8000-000000000003")
FORECAST_ID = UUID("00000000-0000-4000-8000-000000000004")


def valid_forecast(**overrides):
    forecast = {
        "id": str(FORECAST_ID),
        "origin_location_id": ORIGIN,
        "destination_location_id": DESTINATION,
        "vessel_class": "Panamax",
        "unit": "USD/MT",
        "p10": 28.0,
        "p50": 31.0,
        "p90": 35.0,
        "provenance": "FORECAST",
        "model_name": "test-model",
        "generated_at": "2026-10-26T10:00:00+00:00",
        "metadata": {
            "route_scoped": True,
            "input_provenance": "MARKET_OBSERVATION",
            "observation_count": 12,
            "distinct_observation_dates": 12,
            "source_provenances": ["REAL"],
            "source_labels": ["Verified test provider"],
        },
    }
    forecast.update(overrides)
    return forecast


def valid_cargo(**overrides):
    cargo = {
        "id": str(CARGO_ID),
        "origin_location_id": ORIGIN,
        "destination_location_id": DESTINATION,
        "vessel_class": "Panamax",
        "quantity_mt": "12500.5",
    }
    cargo.update(overrides)
    return cargo


def request(**overrides):
    values = {
        "forecast_id": FORECAST_ID,
        "cargo_requirement_id": CARGO_ID,
        "cargo_quantity_mt": 12500.5,
        "wait_days": 7,
        "simulations": 100,
        "seed": 42,
        "currency": "USD",
    }
    values.update(overrides)
    return DecisionRequest(**values)


def test_decision_rejects_legacy_static_forecast(monkeypatch):
    monkeypatch.setattr(
        decision_engine,
        "_get_forecast",
        lambda _forecast_id: valid_forecast(provenance="PUBLIC_PROXY_REFERENCE"),
    )
    monkeypatch.setattr(
        decision_engine,
        "_get_cargo_requirement",
        lambda _cargo_id: valid_cargo(),
    )

    with pytest.raises(ValueError, match="proxy or demo reference"):
        decision_engine.evaluate_decision(request())


@pytest.mark.parametrize(
    ("forecast_changes", "message"),
    [
        ({"unit": "USD_per_40ft_container"}, "only supports freight rates in USD/MT"),
        ({"p10": 40.0, "p50": 30.0, "p90": 50.0}, "ordered P10"),
        ({"metadata": {**valid_forecast()["metadata"], "route_scoped": False}}, "unscoped forecast"),
        ({"origin_location_id": None}, "exact, distinct origin"),
    ],
)
def test_decision_rejects_ineligible_forecast_before_risk_calculation(
    monkeypatch, forecast_changes, message
):
    monkeypatch.setattr(
        decision_engine,
        "_get_forecast",
        lambda _forecast_id: valid_forecast(**forecast_changes),
    )

    with pytest.raises(ValueError, match=message):
        decision_engine.evaluate_decision(request())


@pytest.mark.parametrize(
    ("cargo_changes", "requested_quantity", "message"),
    [
        ({"origin_location_id": DESTINATION}, 12500.5, "does not match the saved procurement route"),
        ({"destination_location_id": ORIGIN}, 12500.5, "does not match the saved procurement route"),
        ({"vessel_class": "Capesize"}, 12500.5, "does not match the saved procurement vessel class"),
        ({"vessel_class": None}, 12500.5, "does not match the saved procurement vessel class"),
        ({}, 12500.75, "does not match the saved procurement requirement"),
    ],
)
def test_decision_rejects_saved_cargo_mismatch(monkeypatch, cargo_changes, requested_quantity, message):
    monkeypatch.setattr(
        decision_engine,
        "_get_forecast",
        lambda _forecast_id: valid_forecast(),
    )
    monkeypatch.setattr(
        decision_engine,
        "_get_cargo_requirement",
        lambda _cargo_id: valid_cargo(**cargo_changes),
    )

    with pytest.raises(ValueError, match=message):
        decision_engine.evaluate_decision(request(cargo_quantity_mt=requested_quantity))


def test_decision_succeeds_for_eligible_forecast_and_exact_saved_cargo(monkeypatch):
    monkeypatch.setattr(
        decision_engine,
        "_get_forecast",
        lambda _forecast_id: valid_forecast(),
    )
    monkeypatch.setattr(
        decision_engine,
        "_get_cargo_requirement",
        lambda _cargo_id: valid_cargo(),
    )

    result = decision_engine.evaluate_decision(request())

    assert result.forecast_p50 == 31.0
    assert result.cargo_quantity_mt == 12500.5
    assert result.provenance == "REAL"
    assert result.route_snapshot["validation_status"] == "SOURCE_MATCHED"


@pytest.mark.parametrize("quantity", [float("inf"), float("-inf"), float("nan"), 0, -1])
def test_decision_request_rejects_non_finite_or_non_positive_quantity(quantity):
    with pytest.raises(ValidationError):
        request(cargo_quantity_mt=quantity)


def test_decision_request_rejects_non_usd_currency_until_fx_is_modeled():
    with pytest.raises(ValidationError):
        request(currency="EUR")
