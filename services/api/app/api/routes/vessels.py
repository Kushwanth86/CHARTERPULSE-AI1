from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from services.api.app.schemas.vessels import (
    VesselCreate,
    VesselResponse,
)
from services.api.app.services.vessel_service import VesselService


router = APIRouter(
    prefix="/api/v1/vessels",
    tags=["vessels"],
)

service = VesselService()


@router.post(
    "",
    response_model=VesselResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_vessel(payload: VesselCreate):
    return service.create(payload)


@router.get(
    "",
    response_model=list[VesselResponse],
)
def list_vessels(
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
    ),
):
    return service.list(limit)


@router.get(
    "/{vessel_id}",
    response_model=VesselResponse,
)
def get_vessel(vessel_id: UUID):

    result = service.get(vessel_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Vessel not found.",
        )

    return result
