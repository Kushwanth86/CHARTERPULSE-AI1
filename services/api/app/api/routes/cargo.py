from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from services.api.app.schemas.cargo import (
    CargoRequirementCreate,
    CargoRequirementResponse,
)
from services.api.app.services.cargo_service import CargoService


router = APIRouter(
    prefix="/api/v1/cargo",
    tags=["cargo"],
)

service = CargoService()


@router.post(
    "",
    response_model=CargoRequirementResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_cargo(payload: CargoRequirementCreate):
    return service.create(payload)


@router.get(
    "",
    response_model=list[CargoRequirementResponse],
)
def list_cargo(
    limit: int = Query(default=100, ge=1, le=500),
):
    return service.list(limit)


@router.get(
    "/{cargo_id}",
    response_model=CargoRequirementResponse,
)
def get_cargo(cargo_id: UUID):
    result = service.get(cargo_id)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cargo requirement not found.",
        )

    return result
