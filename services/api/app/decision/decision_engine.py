from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, Field

from services.api.app.repositories.supabase_client import (
    get_supabase_admin_client,
)
from risk.risk_engine import simulate_freight_risk


class DecisionRequest(BaseModel):
    forecast_id: UUID
    cargo_requirement_id: UUID | None = None
    cargo_quantity_mt: float = Field(gt=0)
    wait_days: int = Field(default=7, ge=1, le=365)
    simulations: int = Field(default=5000, ge=100, le=100000)
    seed: int = 42
    currency: str = "USD"


class DecisionResponse(BaseModel):
    decision_run_id: str | None = None

    decision_status: str
    recommendation: str

    cargo_quantity_mt: float
    currency: str

    forecast_p10: float
    forecast_p50: float
    forecast_p90: float

    now_expected_freight_cost: float
    now_p90_freight_cost: float

    wait_conservative_rate: float
    wait_conservative_cost: float

    wait_cost_difference: float
    wait_cost_difference_per_mt: float

    probability_now_exceeds_baseline: float
    risk_score: float

    provenance: str
    model_name: str | None
    forecast_id: UUID

    rationale: list[str]
    warnings: list[str]

    generated_at: datetime


def _get_forecast(forecast_id: UUID) -> dict:

    client = get_supabase_admin_client()

    response = (
        client.table("freight_forecasts")
        .select("*")
        .eq("id", str(forecast_id))
        .limit(1)
        .execute()
    )

    if not response.data:
        raise ValueError(
            f"Forecast {forecast_id} was not found."
        )

    return response.data[0]


def evaluate_decision(
    payload: DecisionRequest,
) -> DecisionResponse:

    forecast = _get_forecast(payload.forecast_id)

    p10 = forecast.get("p10")
    p50 = forecast.get("p50")
    p90 = forecast.get("p90")

    if p10 is None or p50 is None or p90 is None:
        raise ValueError(
            "Decision evaluation requires P10, P50 and P90."
        )

    risk = simulate_freight_risk(
        p10=float(p10),
        p50=float(p50),
        p90=float(p90),
        cargo_quantity_mt=payload.cargo_quantity_mt,
        baseline_rate=float(p50),
        simulations=payload.simulations,
        seed=payload.seed,
    )

    now_expected_cost = risk.expected_cost
    now_p90_cost = risk.p90_cost

    # Conservative WAIT representation.
    # This is a forecast-derived scenario, not an observed
    # future market price.
    wait_rate = float(p90)
    wait_cost = wait_rate * payload.cargo_quantity_mt

    difference = wait_cost - now_expected_cost
    difference_per_mt = (
        difference / payload.cargo_quantity_mt
    )

    rationale = [
        f"Forecast P50 is {float(p50):.4f} {payload.currency}/MT.",
        f"Forecast P90 is {float(p90):.4f} {payload.currency}/MT.",
        f"Monte Carlo expected NOW freight cost is "
        f"{now_expected_cost:,.2f} {payload.currency}.",
        f"Conservative WAIT freight cost uses P90: "
        f"{wait_cost:,.2f} {payload.currency}.",
        f"Modeled WAIT minus expected NOW is "
        f"{difference:,.2f} {payload.currency}.",
        f"Probability of freight exceeding the current P50 "
        f"baseline is {risk.probability_cost_above_baseline:.2%}.",
    ]

    warnings = [
        "PRELIMINARY decision: only freight uncertainty is modeled.",
        "Bunker/fuel cost is not modeled.",
        "Port and canal charges are not modeled.",
        "Loading/discharge costs are not modeled.",
        "Demurrage and storage are not modeled.",
        "Vessel delay and weather risk are not modeled.",
        "Inland logistics and insurance are not modeled.",
        "WAIT uses forecast P90 as a conservative scenario, "
        "not an observed future market price.",
        f"WAIT horizon is {payload.wait_days} days.",
    ]

    if difference > 0:
        recommendation = "CHARTER_NOW"
        rationale.append(
            "The conservative WAIT scenario is more expensive "
            "than the modeled expected NOW freight cost."
        )
    elif difference < 0:
        recommendation = "WAIT"
        rationale.append(
            "The conservative WAIT scenario is cheaper than "
            "the modeled expected NOW freight cost."
        )
    else:
        recommendation = "REVIEW"
        rationale.append(
            "The modeled NOW and WAIT freight costs are equal."
        )

    return DecisionResponse(
        decision_status="PRELIMINARY",
        recommendation=recommendation,
        cargo_quantity_mt=payload.cargo_quantity_mt,
        currency=payload.currency,
        forecast_p10=float(p10),
        forecast_p50=float(p50),
        forecast_p90=float(p90),
        now_expected_freight_cost=now_expected_cost,
        now_p90_freight_cost=now_p90_cost,
        wait_conservative_rate=wait_rate,
        wait_conservative_cost=round(wait_cost, 2),
        wait_cost_difference=round(difference, 2),
        wait_cost_difference_per_mt=round(
            difference_per_mt,
            4,
        ),
        probability_now_exceeds_baseline=(
            risk.probability_cost_above_baseline
        ),
        risk_score=risk.risk_score,
        provenance="FORECAST",
        model_name=forecast.get("model_name"),
        forecast_id=payload.forecast_id,
        rationale=rationale,
        warnings=warnings,
        generated_at=datetime.now(timezone.utc),
    )


