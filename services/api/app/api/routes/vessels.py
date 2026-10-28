from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from services.api.app.schemas.vessels import VesselCreate, VesselResponse
from services.api.app.security.current_user import get_current_user_id
from services.api.app.services.vessel_service import VesselService


router = APIRouter(prefix="/api/v1/vessels", tags=["vessels"])
service = VesselService()


@router.post("", response_model=VesselResponse, status_code=status.HTTP_201_CREATED)
def create_vessel(
    payload: VesselCreate,
    user_id: UUID = Depends(get_current_user_id),
):
    return service.create(payload, user_id)


@router.get("", response_model=list[VesselResponse])
def list_vessels(
    limit: int = Query(default=100, ge=1, le=500),
    user_id: UUID = Depends(get_current_user_id),
):
    return service.list(user_id, limit)


@router.get("/{vessel_id}", response_model=VesselResponse)
def get_vessel(
    vessel_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
):
    result = service.get(vessel_id, user_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vessel not found.",
        )
    return result
