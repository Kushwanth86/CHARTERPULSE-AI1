from uuid import UUID

from fastapi import APIRouter, HTTPException

from services.api.app.schemas.port_constraints import (
    PortConstraintCreate,
    PortConstraintResponse,
)
from services.api.app.services.port_constraint_service import (
    PortConstraintService,
)


router = APIRouter(
    prefix="/api/v1/port-constraints",
    tags=["port-constraints"],
)

service = PortConstraintService()


@router.post("", response_model=PortConstraintResponse)
def create_port_constraint(payload: PortConstraintCreate):
    return service.create(payload)


@router.get("", response_model=list[PortConstraintResponse])
def list_port_constraints():
    return service.list()


@router.get("/{port_id}", response_model=PortConstraintResponse)
def get_port_constraint(port_id: UUID):
    result = service.get_by_port(port_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Port constraint not found",
        )

    return result
