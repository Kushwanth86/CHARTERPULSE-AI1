from fastapi import APIRouter

from services.api.app.schemas.human_decision import (
    HumanDecisionCreate,
    HumanDecisionResponse,
)
from services.api.app.services.human_decision_service import (
    human_decision_service,
)


router = APIRouter(
    prefix="/api/v1/decisions",
    tags=["Human Decisions"],
)


@router.post(
    "/human",
    response_model=HumanDecisionResponse,
)
def create_human_decision(
    payload: HumanDecisionCreate,
) -> HumanDecisionResponse:
    return human_decision_service.create_decision(payload)
