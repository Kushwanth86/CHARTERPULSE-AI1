from uuid import UUID

from pydantic import BaseModel


class FeasibilityRequest(BaseModel):
    cargo_requirement_id: UUID

    vessel_id: UUID

    origin_port_id: UUID
    destination_port_id: UUID


class FeasibilityResponse(BaseModel):
    id: UUID

    cargo_requirement_id: UUID
    vessel_id: UUID

    origin_port_id: UUID
    destination_port_id: UUID

    result: str

    cargo_capacity_ok: bool | None
    cargo_compatibility_ok: bool | None

    origin_loa_ok: bool | None
    origin_beam_ok: bool | None
    origin_draft_ok: bool | None

    destination_loa_ok: bool | None
    destination_beam_ok: bool | None
    destination_draft_ok: bool | None

    loading_capability_ok: bool | None
    discharge_capability_ok: bool | None

    delivery_window_ok: bool | None

    reasons: list
    checks: dict

    provenance: str
