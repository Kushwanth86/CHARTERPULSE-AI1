from services.api.app.repositories.vessel_cargo_compatibility_repository import (
    VesselCargoCompatibilityRepository,
)


class VesselCargoCompatibilityService:

    def __init__(self):
        self.repository = VesselCargoCompatibilityRepository()

    def create(self, payload: dict) -> dict:
        if not payload.get("cargo_type") and not payload.get("material"):
            raise ValueError("cargo_type or material is required.")
        return self.repository.create(payload)

    def list_for_vessel(self, vessel_id):
        return self.repository.list_for_vessel(vessel_id)
