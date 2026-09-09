from services.api.app.repositories.supabase_client import get_supabase_admin_client
from services.api.app.schemas.costs import (
    CostComponent,
    TotalDeliveredCostRequest,
    TotalDeliveredCostResponse,
)

COMPONENTS = [
    ("ocean_freight_per_mt", "Ocean Freight"),
    ("bunker_cost", "Bunker / Fuel"),
    ("port_cost", "Port Charges"),
    ("canal_cost", "Canal Charges"),
    ("loading_cost", "Loading"),
    ("discharge_cost", "Discharge"),
    ("demurrage_cost", "Demurrage"),
    ("storage_cost", "Storage"),
    ("insurance_cost", "Insurance"),
    ("delay_cost", "Delay"),
    ("inland_cost", "Inland Logistics"),
    ("risk_cost", "Risk Premium"),
]


def _get_forecast(forecast_id):
    if forecast_id is None:
        return None

    client = get_supabase_admin_client()

    response = (
        client.table("freight_forecasts")
        .select("*")
        .eq("id", str(forecast_id))
        .limit(1)
        .execute()
    )

    return response.data[0] if response.data else None


def calculate_total_delivered_cost(
    payload: TotalDeliveredCostRequest,
) -> TotalDeliveredCostResponse:

    warnings: list[str] = []
    components: list[CostComponent] = []

    known_count = 0
    missing_count = 0
    total = 0.0

    forecast = _get_forecast(payload.forecast_id)

    ocean_freight = payload.ocean_freight_per_mt
    ocean_provenance = "USER_PROVIDED"
    ocean_source = None
    ocean_reference = None
    ocean_observed_at = None

    if ocean_freight is None and payload.forecast_id is not None:
        if forecast is None:
            raise ValueError(
                f"Forecast {payload.forecast_id} was not found."
            )

        if forecast.get("p50") is None:
            raise ValueError(
                f"Forecast {payload.forecast_id} has no P50 value."
            )

        ocean_freight = float(forecast["p50"])
        ocean_provenance = "FORECAST"
        ocean_source = forecast.get("model_name")
        ocean_reference = str(payload.forecast_id)
        ocean_observed_at = forecast.get("generated_at")

    for field_name, display_name in COMPONENTS:

        value = getattr(payload, field_name)

        if field_name == "ocean_freight_per_mt":
            value = ocean_freight

        if value is None:
            missing_count += 1

            warnings.append(
                f"{display_name} is unavailable and was excluded "
                "from the calculated total."
            )
            continue

        amount = float(value)

        if field_name == "ocean_freight_per_mt":
            amount = amount * payload.cargo_quantity_mt

            components.append(
                CostComponent(
                    name=display_name,
                    amount=amount,
                    currency=payload.currency,
                    unit="TOTAL",
                    provenance=ocean_provenance,
                    source=ocean_source,
                    source_reference=ocean_reference,
                    observed_at=ocean_observed_at,
                    status="DERIVED" if ocean_provenance == "FORECAST"
                    else "KNOWN",
                )
            )
        else:
            components.append(
                CostComponent(
                    name=display_name,
                    amount=amount,
                    currency=payload.currency,
                    unit="TOTAL",
                    provenance="USER_PROVIDED",
                    status="KNOWN",
                )
            )

        known_count += 1
        total += amount

    component_count = known_count + missing_count
    completeness = (
        known_count / component_count
        if component_count > 0
        else 0.0
    )

    if missing_count:
        warnings.insert(
            0,
            f"{missing_count} cost components are unavailable. "
            "This is a partial delivered-cost estimate."
        )

    provenance = (
        "DERIVED"
        if ocean_provenance == "FORECAST"
        else "USER_PROVIDED"
    )

    return TotalDeliveredCostResponse(
        total_cost=round(total, 2),
        cost_per_mt=round(total / payload.cargo_quantity_mt, 4),
        currency=payload.currency,
        completeness_score=round(completeness, 4),
        components=components,
        known_component_count=known_count,
        missing_component_count=missing_count,
        provenance=provenance,
        warnings=warnings,
    )
