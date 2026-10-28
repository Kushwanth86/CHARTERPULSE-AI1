import math

import pytest

from risk.risk_engine import simulate_freight_risk


def run_risk(**overrides):
    values = {
        "p10": 20.0,
        "p50": 25.0,
        "p90": 30.0,
        "cargo_quantity_mt": 12500.5,
        "baseline_rate": 25.0,
        "simulations": 100,
        "seed": 42,
    }
    values.update(overrides)
    return simulate_freight_risk(**values)


@pytest.mark.parametrize(
    "field,value",
    [
        ("p10", float("nan")),
        ("p50", float("inf")),
        ("p90", float("-inf")),
        ("cargo_quantity_mt", float("nan")),
        ("baseline_rate", float("inf")),
    ],
)
def test_risk_engine_rejects_non_finite_inputs(field, value):
    with pytest.raises(ValueError, match="finite"):
        run_risk(**{field: value})


@pytest.mark.parametrize(
    "overrides",
    [
        {"p10": -1.0, "p50": 2.0, "p90": 3.0},
        {"p10": 2.0, "p50": 1.0, "p90": 3.0},
        {"p10": 1.0, "p50": 3.0, "p90": 2.0},
        {"p10": 0.0, "p50": 0.0, "p90": 0.0},
    ],
)
def test_risk_engine_rejects_negative_or_unordered_quantiles(overrides):
    with pytest.raises(ValueError, match="quantiles"):
        run_risk(**overrides)


def test_risk_engine_rejects_rate_that_can_overflow_sampling():
    with pytest.raises(ValueError, match="safe numeric range"):
        run_risk(p10=1e308, p50=1e308, p90=1e308)


def test_risk_engine_rejects_rate_quantity_product_overflow():
    with pytest.raises(ValueError, match="safe numeric range"):
        run_risk(p10=1.0, p50=1.0, p90=1.0, cargo_quantity_mt=1e308)


def test_risk_engine_handles_realistic_large_decimal_quantity_without_overflow():
    result = run_risk(cargo_quantity_mt=1e12, simulations=5000)
    assert math.isfinite(result.expected_cost)
    assert math.isfinite(result.p90_cost)
    assert math.isfinite(result.risk_score)
