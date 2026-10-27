from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from services.api.app.schemas.cargo import (
    CargoRequirementCreate,
    CargoRequirementResponse,
)
from services.api.app.security.current_user import get_current_user_id
from services.api.app.services.cargo_service import CargoService


router = APIRouter(prefix="/api/v1/cargo", tags=["cargo"])
service = CargoService()


@router.post(
    "",
    response_model=CargoRequirementResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_cargo(
    payload: CargoRequirementCreate,
    user_id: UUID = Depends(get_current_user_id),
):
    return service.create(payload, user_id)


@router.get("", response_model=list[CargoRequirementResponse])
def list_cargo(
    limit: int = Query(default=100, ge=1, le=500),
    user_id: UUID = Depends(get_current_user_id),
):
    return service.list(user_id, limit)


@router.get("/{cargo_id}", response_model=CargoRequirementResponse)
def get_cargo(
    cargo_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
):
    result = service.get(cargo_id, user_id)
    if result is None:
        # Do not reveal whether the UUID belongs to a different user.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cargo requirement not found.",
        )
    return result
