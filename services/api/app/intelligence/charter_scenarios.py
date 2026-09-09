from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, Field

from services.api.app.repositories.supabase_client import (
    get_supabase_admin_client,
)


class CharterScenarioRequest(BaseModel):
    forecast_id: UUID
    cargo_quantity_mt: float = Field(gt=0)
    wait_days: int = Field(default=7, ge=1, le=365)
    currency: str = "USD"


class CharterScenario(BaseModel):
    strategy: str
    freight_rate_per_mt: float
    freight_cost: float
    cargo_quantity_mt: float
    currency: str
    provenance: str
    forecast_quantile: str
    assumptions: list[str]


class CharterScenarioResponse(BaseModel):
    now: CharterScenario
    wait: CharterScenario
    expected_savings_if_wait: float
    expected_savings_per_mt_if_wait: float
    recommendation: str
    rationale: list[str]
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


def calculate_charter_scenarios(
    payload: CharterScenarioRequest,
) -> CharterScenarioResponse:

    forecast = _get_forecast(payload.forecast_id)

    p10 = forecast.get("p10")
    p50 = forecast.get("p50")
    p90 = forecast.get("p90")

    if p10 is None or p50 is None or p90 is None:
        raise ValueError(
            "Forecast must contain P10, P50 and P90 "
            "before scenario analysis can run."
        )

    quantity = payload.cargo_quantity_mt

    now_rate = float(p50)

    # Conservative WAIT assumption:
    # use the forecast upper quantile rather than pretending
    # we know the exact future market price.
    wait_rate = float(p90)

    now_cost = now_rate * quantity
    wait_cost = wait_rate * quantity

    savings = now_cost - wait_cost
    savings_per_mt = savings / quantity

    if wait_rate < now_rate:
        recommendation = "WAIT"
    elif wait_rate > now_rate:
        recommendation = "CHARTER_NOW"
    else:
        recommendation = "REVIEW"

    rationale = [
        f"Current forecast P50 is {now_rate:.4f} {payload.currency}/MT.",
        f"WAIT scenario uses forecast P90 of {wait_rate:.4f} "
        f"{payload.currency}/MT.",
        "P90 is used as a conservative future-price assumption; "
        "it is not an observed future market price.",
    ]

    if recommendation == "CHARTER_NOW":
        rationale.append(
            "The modeled WAIT scenario is more expensive than "
            "the current P50 scenario."
        )
    elif recommendation == "WAIT":
        rationale.append(
            "The modeled WAIT scenario is cheaper than the "
            "current P50 scenario."
        )
    else:
        rationale.append(
            "The modeled scenarios are equal; human review is required."
        )

    assumptions = [
        "Scenario is forecast-derived.",
        "No additional bunker, port, canal, storage, delay, "
        "insurance or inland costs are included.",
        f"WAIT horizon is {payload.wait_days} days.",
        "Future freight is represented by a forecast quantile, "
        "not fabricated market data.",
    ]

    now = CharterScenario(
        strategy="CHARTER_NOW",
        freight_rate_per_mt=round(now_rate, 4),
        freight_cost=round(now_cost, 2),
        cargo_quantity_mt=quantity,
        currency=payload.currency,
        provenance="FORECAST",
        forecast_quantile="P50",
        assumptions=assumptions,
    )

    wait = CharterScenario(
        strategy="WAIT",
        freight_rate_per_mt=round(wait_rate, 4),
        freight_cost=round(wait_cost, 2),
        cargo_quantity_mt=quantity,
        currency=payload.currency,
        provenance="FORECAST",
        forecast_quantile="P90",
        assumptions=assumptions,
    )

    return CharterScenarioResponse(
        now=now,
        wait=wait,
        expected_savings_if_wait=round(savings, 2),
        expected_savings_per_mt_if_wait=round(savings_per_mt, 4),
        recommendation=recommendation,
        rationale=rationale,
        generated_at=datetime.now(timezone.utc),
    )
