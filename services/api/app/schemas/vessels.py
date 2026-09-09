from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class VesselCreate(BaseModel):
    imo_number: str | None = None
    mmsi: str | None = None

    name: str = Field(min_length=1)

    vessel_class: str | None = None
    ship_type: str | None = None
    flag: str | None = None

    dwt_mt: float | None = Field(default=None, gt=0)
    gross_tonnage: float | None = Field(default=None, gt=0)

    loa_m: float | None = Field(default=None, gt=0)
    beam_m: float | None = Field(default=None, gt=0)
    max_draft_m: float | None = Field(default=None, gt=0)

    cargo_capacity_mt: float | None = Field(default=None, gt=0)

    year_built: int | None = None

    source: str | None = None
    source_reference: str | None = None

    provenance: str = "USER_PROVIDED"
    observed_at: datetime | None = None


class VesselResponse(VesselCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime
