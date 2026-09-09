from fastapi import APIRouter, HTTPException

from services.api.app.schemas.feasibility import (
    FeasibilityRequest,
    FeasibilityResponse,
)
from services.api.app.services.feasibility_service import (
    FeasibilityService,
)


router = APIRouter(
    prefix="/api/v1/feasibility",
    tags=["feasibility"],
)

service = FeasibilityService()


@router.post(
    "",
    response_model=FeasibilityResponse,
)
def evaluate_feasibility(
    payload: FeasibilityRequest,
):

    try:
        return service.evaluate(payload)

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
