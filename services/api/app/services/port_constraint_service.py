from uuid import UUID

from services.api.app.repositories.port_constraint_repository import (
    PortConstraintRepository,
)


class PortConstraintService:
    def __init__(self):
        self.repository = PortConstraintRepository()

    def create(self, payload):
        return self.repository.create(
            payload.model_dump(mode="json")
        )

    def list(self):
        return self.repository.list()

    def get_by_port(self, port_id: UUID):
        return self.repository.get(port_id)
