from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class VesselCargoCompatibilityCreate(BaseModel):
    vessel_id: UUID
    cargo_type: str | None = None
    material: str | None = None
    allowed: bool = True

    source: str | None = None
    source_reference: str | None = None
    provenance: str = "USER_PROVIDED"
    observed_at: datetime | None = None


class VesselCargoCompatibilityResponse(VesselCargoCompatibilityCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime
