from uuid import UUID

from services.api.app.repositories.cargo_repository import CargoRepository
from services.api.app.schemas.cargo import CargoRequirementCreate


class CargoService:
    def __init__(self):
        self.repository = CargoRepository()

    def create(self, payload: CargoRequirementCreate, user_id: UUID) -> dict:
        data = payload.model_dump(mode="json")
        return self.repository.create(data, user_id)

    def get(self, cargo_id: UUID, user_id: UUID) -> dict | None:
        return self.repository.get(cargo_id, user_id)

    def list(self, user_id: UUID, limit: int = 100) -> list[dict]:
        return self.repository.list(user_id, limit)
