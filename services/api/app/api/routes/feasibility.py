from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from services.api.app.security.current_user import get_current_user_id
from services.api.app.schemas.feasibility import FeasibilityRequest, FeasibilityResponse
from services.api.app.services.feasibility_service import FeasibilityService


router = APIRouter(
    prefix="/api/v1/feasibility",
    tags=["feasibility"],
)

service = FeasibilityService()


@router.post("", response_model=FeasibilityResponse)
def evaluate_feasibility(
    payload: FeasibilityRequest,
    user_id: UUID = Depends(get_current_user_id),
):
    try:
        return service.evaluate(payload, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
