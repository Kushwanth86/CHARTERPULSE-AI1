from fastapi import APIRouter

from services.api.app.schemas.risk import (
    RiskSimulationRequest,
    RiskSimulationResponse,
)
from services.api.app.services.risk_service import calculate_risk

router = APIRouter(
    prefix="/api/v1/risk",
    tags=["risk"],
)


@router.post(
    "/simulate",
    response_model=RiskSimulationResponse,
)
def simulate_risk(payload: RiskSimulationRequest):
    return calculate_risk(payload)
