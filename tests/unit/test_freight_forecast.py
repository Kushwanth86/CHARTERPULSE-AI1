from datetime import datetime, timedelta, timezone

import pytest

from services.api.app.intelligence.freight_forecast import (
    FreightForecastEngine,
)


def observations(values: list[float]) -> list[dict]:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [
        {
            "value": value,
            "observed_at": (start + timedelta(days=index)).isoformat(),
        }
        for index, value in enumerate(values)
    ]


def test_forecast_requires_observations():
    engine = FreightForecastEngine()

    with pytest.raises(ValueError, match="No usable freight observations"):
        engine.forecast([], horizon_days=7)


def test_forecast_returns_ordered_prediction_interval():
    engine = FreightForecastEngine()

    result = engine.forecast(
        observations([20, 21, 22, 23, 24, 25]),
        horizon_days=7,
    )

    assert result["provenance"] == "FORECAST"
    assert result["p10"] <= result["p50"] <= result["p90"]
    assert result["baseline_value"] == result["p50"]
    assert result["confidence"] >= 0
    assert result["confidence"] <= 1
    assert result["metadata"]["observation_count"] == 6


def test_forecast_exposes_model_and_backtest_metrics():
    engine = FreightForecastEngine()

    result = engine.forecast(
        observations([30, 31, 29, 32, 34, 33, 35, 36]),
        horizon_days=14,
    )

    assert result["model_name"] == "robust_recency_trend_baseline"
    assert result["model_version"] == "1.0.0"
    assert result["mae"] is not None
    assert result["rmse"] is not None
    assert result["smape"] is not None


def test_invalid_market_values_are_ignored():
    engine = FreightForecastEngine()

    result = engine.forecast(
        [
            {"value": 20, "observed_at": "2026-01-01T00:00:00+00:00"},
            {"value": -5, "observed_at": "2026-01-02T00:00:00+00:00"},
            {"value": "bad", "observed_at": "2026-01-03T00:00:00+00:00"},
            {"value": 22, "observed_at": "2026-01-04T00:00:00+00:00"},
        ],
        horizon_days=7,
    )

    assert result["metadata"]["observation_count"] == 2
    assert result["p50"] > 0
