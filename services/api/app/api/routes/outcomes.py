from uuid import UUID

from fastapi import APIRouter, Depends

from services.api.app.security.current_user import get_current_user_id
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
    user_id: UUID = Depends(get_current_user_id),
) -> DecisionOutcomeResponse:
    return outcome_service.create_outcome(payload, user_id)


@router.post(
    "/decision-feedback",
    response_model=DecisionFeedbackResponse,
)
def create_decision_feedback(
    payload: DecisionFeedbackCreate,
    user_id: UUID = Depends(get_current_user_id),
) -> DecisionFeedbackResponse:
    return feedback_service.create_feedback(payload, user_id)
