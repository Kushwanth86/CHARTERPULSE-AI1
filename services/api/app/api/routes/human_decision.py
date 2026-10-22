from fastapi import APIRouter, Query

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


@router.get(
    "/human",
    response_model=list[HumanDecisionResponse],
)
def list_human_decisions(
    limit: int = Query(default=100, ge=1, le=500),
) -> list[HumanDecisionResponse]:
    return human_decision_service.list_decisions(limit=limit)


@router.post(
    "/human",
    response_model=HumanDecisionResponse,
)
def create_human_decision(
    payload: HumanDecisionCreate,
) -> HumanDecisionResponse:
    return human_decision_service.create_decision(payload)
