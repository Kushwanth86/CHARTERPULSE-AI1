from datetime import datetime, timedelta, timezone

from services.api.app.intelligence.freight_forecast import FreightForecastEngine


def observations(values: list[float]) -> list[dict]:
    start = datetime(2026, 9, 1, tzinfo=timezone.utc)
    return [
        {
            "value": value,
            "observed_at": (start + timedelta(days=index)).isoformat(),
        }
        for index, value in enumerate(values)
    ]


def test_confidence_changes_when_three_observations_have_meaningfully_different_dispersion():
    engine = FreightForecastEngine()

    stable = engine.forecast(
        observations([30.0, 30.1, 30.2]),
        horizon_days=7,
    )
    volatile = engine.forecast(
        observations([20.0, 30.0, 40.0]),
        horizon_days=7,
    )

    assert stable["confidence"] > volatile["confidence"]


def test_confidence_is_limited_by_small_sample_even_when_trend_is_stable():
    engine = FreightForecastEngine()

    result = engine.forecast(
        observations([28.4, 30.1, 31.5]),
        horizon_days=7,
    )

    assert result["metadata"]["observation_count"] == 3
    assert result["confidence"] < 0.20


def test_confidence_increases_as_evidence_accumulates_for_same_stable_process():
    engine = FreightForecastEngine()

    short = engine.forecast(
        observations([30.0, 30.1, 30.2]),
        horizon_days=7,
    )
    long = engine.forecast(
        observations([30.0, 30.1, 30.2] * 10),
        horizon_days=7,
    )

    assert long["confidence"] > short["confidence"]
