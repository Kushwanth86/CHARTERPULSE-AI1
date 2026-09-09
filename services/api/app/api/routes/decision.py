from fastapi import APIRouter

from services.api.app.decision.decision_engine import (
    DecisionRequest,
    DecisionResponse,
)
from services.api.app.services.decision_service import (
    DecisionService,
)

router = APIRouter(
    prefix="/api/v1/decision",
    tags=["decision"],
)

service = DecisionService()


@router.post(
    "/evaluate",
    response_model=DecisionResponse,
)
def evaluate_decision(payload: DecisionRequest):
    return service.evaluate(payload)
