from fastapi import APIRouter

from services.api.app.schemas.outcomes import (
    DecisionFeedbackCreate,
    DecisionFeedbackResponse,
    DecisionOutcomeCreate,
    DecisionOutcomeResponse,
)
from services.api.app.services.outcome_service import (
    feedback_service,
    outcome_service,
)


router = APIRouter(
    prefix="/api/v1",
    tags=["decision-outcomes"],
)


@router.post(
    "/decision-outcomes",
    response_model=DecisionOutcomeResponse,
)
def create_decision_outcome(
    payload: DecisionOutcomeCreate,
) -> DecisionOutcomeResponse:
    return outcome_service.create_outcome(payload)


@router.post(
    "/decision-feedback",
    response_model=DecisionFeedbackResponse,
)
def create_decision_feedback(
    payload: DecisionFeedbackCreate,
) -> DecisionFeedbackResponse:
    return feedback_service.create_feedback(payload)
