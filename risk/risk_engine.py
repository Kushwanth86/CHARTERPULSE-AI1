from dataclasses import dataclass
import math
import random


@dataclass
class RiskSimulationResult:
    scenario: str
    simulations: int
    expected_rate_per_mt: float
    p10_rate_per_mt: float
    p50_rate_per_mt: float
    p90_rate_per_mt: float
    expected_cost: float
    p90_cost: float
    probability_cost_above_baseline: float
    risk_score: float
    provenance: str


def _normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def simulate_freight_risk(
    *,
    p10: float,
    p50: float,
    p90: float,
    cargo_quantity_mt: float,
    baseline_rate: float,
    simulations: int = 5000,
    seed: int = 42,
) -> RiskSimulationResult:

    if not (p10 <= p50 <= p90):
        raise ValueError("Forecast quantiles must satisfy P10 <= P50 <= P90.")

    if cargo_quantity_mt <= 0:
        raise ValueError("Cargo quantity must be greater than zero.")

    if simulations < 100:
        raise ValueError("At least 100 simulations are required.")

    # Approximate a normal distribution from the forecast interval.
    # P10/P90 are approximately +/-1.2816 standard deviations.
    sigma = max(
        (p90 - p10) / (2.0 * 1.2815515655446004),
        1e-9,
    )

    rng = random.Random(seed)

    rates = []

    for _ in range(simulations):
        sampled = rng.gauss(p50, sigma)

        # Do not permit physically meaningless negative freight rates.
        sampled = max(sampled, 0.0)

        rates.append(sampled)

    rates.sort()

    expected_rate = sum(rates) / len(rates)

    def percentile(values, percentile):
        index = (len(values) - 1) * percentile
        lower = math.floor(index)
        upper = math.ceil(index)

        if lower == upper:
            return values[lower]

        weight = index - lower
        return (
            values[lower] * (1.0 - weight)
            + values[upper] * weight
        )

    simulated_p10 = percentile(rates, 0.10)
    simulated_p50 = percentile(rates, 0.50)
    simulated_p90 = percentile(rates, 0.90)

    expected_cost = expected_rate * cargo_quantity_mt
    p90_cost = simulated_p90 * cargo_quantity_mt

    above_baseline = sum(
        1 for rate in rates
        if rate > baseline_rate
    )

    probability_above_baseline = (
        above_baseline / simulations
    )

    # Risk score:
    # 0 = low modeled downside
    # 100 = high modeled downside.
    downside_ratio = max(
        (simulated_p90 - baseline_rate) / max(baseline_rate, 1e-9),
        0.0,
    )

    probability_factor = probability_above_baseline

    risk_score = min(
        100.0,
        (
            downside_ratio * 60.0
            + probability_factor * 40.0
        ),
    )

    return RiskSimulationResult(
        scenario="FREIGHT_RISK",
        simulations=simulations,
        expected_rate_per_mt=round(expected_rate, 4),
        p10_rate_per_mt=round(simulated_p10, 4),
        p50_rate_per_mt=round(simulated_p50, 4),
        p90_rate_per_mt=round(simulated_p90, 4),
        expected_cost=round(expected_cost, 2),
        p90_cost=round(p90_cost, 2),
        probability_cost_above_baseline=round(
            probability_above_baseline,
            4,
        ),
        risk_score=round(risk_score, 2),
        provenance="FORECAST",
    )
