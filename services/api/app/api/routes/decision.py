from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from services.api.app.decision.decision_engine import (
    DecisionRequest,
    DecisionResponse,
)
from services.api.app.security.current_user import get_current_user_id
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
def evaluate_decision(
    payload: DecisionRequest,
    user_id: UUID = Depends(get_current_user_id),
):
    try:
        return service.evaluate(payload, user_id)
    except ValueError as exc:
        # Validation failures are expected for unmatched route/evidence; do not
        # surface them as opaque 500s or convert them into fallback prices.
        raise HTTPException(status_code=422, detail=str(exc)) from exc
