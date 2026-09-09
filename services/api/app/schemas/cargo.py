from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CargoRequirementCreate(BaseModel):
    cargo_type: str | None = None
    material: str = Field(min_length=1)
    quantity_mt: float = Field(gt=0)

    origin_location_id: UUID | None = None
    destination_location_id: UUID | None = None

    earliest_delivery: datetime | None = None
    latest_delivery: datetime | None = None

    priority: str = "NORMAL"

    provenance: str = "USER_PROVIDED"
    source: str | None = None
    source_reference: str | None = None


class CargoRequirementResponse(CargoRequirementCreate):
    id: UUID
    status: str

    created_at: datetime
    updated_at: datetime
