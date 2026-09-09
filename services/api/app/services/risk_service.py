from services.api.app.schemas.risk import RiskSimulationRequest
from risk.risk_engine import simulate_freight_risk


def calculate_risk(payload: RiskSimulationRequest):
    return simulate_freight_risk(
        p10=payload.p10,
        p50=payload.p50,
        p90=payload.p90,
        cargo_quantity_mt=payload.cargo_quantity_mt,
        baseline_rate=payload.baseline_rate,
        simulations=payload.simulations,
        seed=payload.seed,
    )
