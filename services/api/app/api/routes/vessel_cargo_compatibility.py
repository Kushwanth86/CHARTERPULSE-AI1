from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from services.api.app.schemas.vessel_cargo_compatibility import (
    VesselCargoCompatibilityCreate,
    VesselCargoCompatibilityResponse,
)
from services.api.app.services.vessel_cargo_compatibility_service import (
    VesselCargoCompatibilityService,
)


router = APIRouter(
    prefix="/api/v1/vessel-cargo-compatibility",
    tags=["vessel-cargo-compatibility"],
)

service = VesselCargoCompatibilityService()


@router.post("", response_model=VesselCargoCompatibilityResponse)
def create_rule(payload: VesselCargoCompatibilityCreate):
    try:
        return service.create(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("", response_model=list[VesselCargoCompatibilityResponse])
def list_rules(vessel_id: UUID = Query(...)):
    return service.list_for_vessel(vessel_id)
