from datetime import datetime, timedelta, timezone

import pytest

from services.api.app.services.forecast_evidence import (
    assert_cargo_matches_forecast,
    assert_decision_eligible_forecast,
    decision_forecast_error,
)


ORIGIN = "00000000-0000-4000-8000-000000000001"
DESTINATION = "00000000-0000-4000-8000-000000000002"


def valid_forecast(**overrides):
    forecast = {
        "id": "forecast-id",
        "origin_location_id": ORIGIN,
        "destination_location_id": DESTINATION,
        "vessel_class": "Panamax",
        "unit": "USD/MT",
        "p10": 28.0,
        "p50": 31.0,
        "p90": 35.0,
        "provenance": "FORECAST",
        "generated_at": "2026-10-26T10:00:00+00:00",
        "metadata": {
            "route_scoped": True,
            "input_provenance": "MARKET_OBSERVATION",
            "observation_count": 12,
            "distinct_observation_dates": 12,
            "source_provenances": ["REAL"],
            "source_labels": ["Verified test provider"],
            "latest_observation_at": datetime.now(timezone.utc).isoformat(),
        },
    }
    forecast.update(overrides)
    return forecast


def test_real_observation_forecast_is_eligible():
    assert_decision_eligible_forecast(valid_forecast())


def test_rejects_stale_market_observation_evidence():
    now = datetime.now(timezone.utc)
    forecast = valid_forecast(
        metadata={
            **valid_forecast()["metadata"],
            "latest_observation_at": (now - timedelta(days=15)).isoformat(),
        }
    )
    assert "older than 14 days" in (decision_forecast_error(forecast) or "")


def test_rejects_future_market_observation_and_generation_timestamps():
    now = datetime.now(timezone.utc)
    stale_clock_forecast = valid_forecast(
        metadata={
            **valid_forecast()["metadata"],
            "latest_observation_at": (now + timedelta(hours=2)).isoformat(),
        }
    )
    future_generated_forecast = valid_forecast(
        generated_at=(now + timedelta(hours=2)).isoformat()
    )

    assert "observation timestamp is in the future" in (
        decision_forecast_error(stale_clock_forecast) or ""
    )
    assert "generation timestamp is in the future" in (
        decision_forecast_error(future_generated_forecast) or ""
    )


def test_rejects_forecast_without_latest_observation_timestamp():
    forecast = valid_forecast(
        metadata={
            **valid_forecast()["metadata"],
        }
    )
    forecast["metadata"].pop("latest_observation_at", None)

    assert "observation timestamp is missing or invalid" in (
        decision_forecast_error(forecast) or ""
    )


def test_public_proxy_forecast_is_eligible_only_with_full_route_evidence():
    forecast = valid_forecast(
        metadata={
            **valid_forecast()["metadata"],
            "source_provenances": ["PUBLIC_PROXY"],
        }
    )
    assert_decision_eligible_forecast(forecast)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"provenance": "PUBLIC_PROXY_REFERENCE"}, "proxy or demo reference"),
        ({"metadata": {**valid_forecast()["metadata"], "input_provenance": "SIMULATED_REFERENCE"}}, "not generated from market observations"),
        ({"unit": "USD_per_40ft_container"}, "only supports freight rates in USD/MT"),
        ({"p10": float("nan")}, "finite numeric values"),
        ({"p10": 32.0, "p50": 31.0, "p90": 35.0}, "ordered P10"),
        ({"origin_location_id": None}, "exact, distinct origin"),
        ({"destination_location_id": ORIGIN}, "exact, distinct origin"),
        ({"generated_at": "not-a-date"}, "timestamp is invalid"),
    ],
)
def test_rejects_legacy_or_malformed_forecasts(changes, message):
    candidate = valid_forecast()
    candidate.update(changes)
    with pytest.raises(ValueError, match=message):
        assert_decision_eligible_forecast(candidate)


@pytest.mark.parametrize(
    ("metadata_changes", "message"),
    [
        ({"observation_count": 2}, "three observations"),
        ({"distinct_observation_dates": 1}, "three observations"),
        ({"source_provenances": ["SIMULATED"]}, "unknown provenance"),
        ({"source_provenances": ["USER_PROVIDED"]}, "unknown provenance"),
        ({"source_provenances": []}, "Source provenance is missing"),
        ({"source_labels": []}, "Traceable source labels are missing"),
        ({"route_scoped": False}, "unscoped forecast"),
    ],
)
def test_rejects_forecasts_without_sufficient_non_simulated_evidence(metadata_changes, message):
    base = valid_forecast()
    candidate = valid_forecast(metadata={**base["metadata"], **metadata_changes})
    assert decision_forecast_error(candidate) is not None
    with pytest.raises(ValueError, match=message):
        assert_decision_eligible_forecast(candidate)


def test_cargo_must_match_exact_saved_route_class_and_quantity():
    forecast = valid_forecast()
    cargo = {
        "origin_location_id": ORIGIN,
        "destination_location_id": DESTINATION,
        "vessel_class": "panamax",
        "quantity_mt": "12500.5",
    }
    assert_cargo_matches_forecast(cargo, forecast, 12500.5)


@pytest.mark.parametrize(
    ("cargo_changes", "quantity", "message"),
    [
        ({"origin_location_id": DESTINATION}, 12500.5, "does not match the saved procurement route"),
        ({"destination_location_id": ORIGIN}, 12500.5, "does not match the saved procurement route"),
        ({"vessel_class": "Capesize"}, 12500.5, "does not match the saved procurement vessel class"),
        ({"vessel_class": None}, 12500.5, "does not match the saved procurement vessel class"),
        ({}, 12500.75, "does not match the saved procurement requirement"),
    ],
)
def test_rejects_mismatched_cargo_and_forecast(cargo_changes, quantity, message):
    forecast = valid_forecast()
    cargo = {
        "origin_location_id": ORIGIN,
        "destination_location_id": DESTINATION,
        "vessel_class": "Panamax",
        "quantity_mt": "12500.5",
        **cargo_changes,
    }
    with pytest.raises(ValueError, match=message):
        assert_cargo_matches_forecast(cargo, forecast, quantity)
