from fastapi import APIRouter

from services.api.app.intelligence.charter_scenarios import (
    CharterScenarioRequest,
    CharterScenarioResponse,
)
from services.api.app.services.charter_scenario_service import (
    CharterScenarioService,
)

router = APIRouter(
    prefix="/api/v1/charter-scenarios",
    tags=["charter-scenarios"],
)

service = CharterScenarioService()


@router.post(
    "/compare",
    response_model=CharterScenarioResponse,
)
def compare_charter_scenarios(
    payload: CharterScenarioRequest,
):
    return service.calculate(payload)
