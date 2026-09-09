from uuid import UUID
from typing import Optional

from pydantic import BaseModel, Field


class PortConstraintCreate(BaseModel):
    port_id: UUID
    max_loa_m: Optional[float] = Field(default=None, gt=0)
    max_beam_m: Optional[float] = Field(default=None, gt=0)
    max_draft_m: Optional[float] = Field(default=None, gt=0)
    cargo_handling_types: Optional[list[str]] = None
    max_vessel_capacity_mt: Optional[float] = Field(default=None, gt=0)
    loading_available: Optional[bool] = None
    discharge_available: Optional[bool] = None
    source: Optional[str] = None
    source_reference: Optional[str] = None
    provenance: str = "USER_PROVIDED"
    observed_at: Optional[str] = None


class PortConstraintResponse(PortConstraintCreate):
    id: UUID
