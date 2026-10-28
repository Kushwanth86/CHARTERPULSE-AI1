from uuid import UUID

from services.api.app.repositories.vessel_repository import VesselRepository
from services.api.app.schemas.vessels import VesselCreate


class VesselService:
    def __init__(self):
        self.repository = VesselRepository()

    def create(self, payload: VesselCreate, user_id: UUID) -> dict:
        return self.repository.create(payload.model_dump(mode="json"), user_id)

    def get(self, vessel_id: UUID, user_id: UUID) -> dict | None:
        return self.repository.get(vessel_id, user_id)

    def list(self, user_id: UUID, limit: int = 100) -> list[dict]:
        return self.repository.list(user_id, limit)
