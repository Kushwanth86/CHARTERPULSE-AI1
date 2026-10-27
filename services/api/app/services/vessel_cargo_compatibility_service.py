from uuid import UUID

from services.api.app.repositories.vessel_cargo_compatibility_repository import (
    VesselCargoCompatibilityRepository,
)
from services.api.app.repositories.vessel_repository import VesselRepository


class VesselCargoCompatibilityService:
    def __init__(self):
        self.repository = VesselCargoCompatibilityRepository()
        self.vessels = VesselRepository()

    def create(self, payload: dict, user_id: UUID) -> dict:
        if not payload.get("cargo_type") and not payload.get("material"):
            raise ValueError("cargo_type or material is required.")
        vessel_id = UUID(str(payload.get("vessel_id")))
        if self.vessels.get(vessel_id, user_id) is None:
            raise ValueError("Vessel not found or is not accessible to this user.")
        return self.repository.create(payload, user_id)

    def list_for_vessel(self, vessel_id: UUID, user_id: UUID) -> list[dict]:
        if self.vessels.get(vessel_id, user_id) is None:
            raise ValueError("Vessel not found or is not accessible to this user.")
        return self.repository.list_for_vessel(vessel_id, user_id)
