from uuid import UUID

from services.api.app.intelligence.physical_feasibility import (
    PhysicalFeasibilityEngine,
)
from services.api.app.repositories.cargo_repository import (
    CargoRepository,
)
from services.api.app.repositories.feasibility_repository import (
    FeasibilityRepository,
)
from services.api.app.repositories.port_constraint_repository import (
    PortConstraintRepository,
)
from services.api.app.repositories.vessel_repository import (
    VesselRepository,
)
from services.api.app.schemas.feasibility import (
    FeasibilityRequest,
)


class FeasibilityService:

    def __init__(self):
        self.cargo_repository = CargoRepository()
        self.vessel_repository = VesselRepository()
        self.constraint_repository = PortConstraintRepository()
        self.feasibility_repository = FeasibilityRepository()

        self.engine = PhysicalFeasibilityEngine()

    def evaluate(
        self,
        payload: FeasibilityRequest,
    ) -> dict:

        cargo = self.cargo_repository.get(
            payload.cargo_requirement_id
        )

        if cargo is None:
            raise ValueError(
                "Cargo requirement not found."
            )

        vessel = self.vessel_repository.get(
            payload.vessel_id
        )

        if vessel is None:
            raise ValueError(
                "Vessel not found."
            )

        origin_constraints = (
            self.constraint_repository.get(
                payload.origin_port_id
            )
        )

        destination_constraints = (
            self.constraint_repository.get(
                payload.destination_port_id
            )
        )

        result = self.engine.evaluate(
            cargo=cargo,
            vessel=vessel,
            origin_constraints=origin_constraints,
            destination_constraints=destination_constraints,
        )

        result.update(
            {
                "cargo_requirement_id": str(
                    payload.cargo_requirement_id
                ),
                "vessel_id": str(
                    payload.vessel_id
                ),
                "origin_port_id": str(
                    payload.origin_port_id
                ),
                "destination_port_id": str(
                    payload.destination_port_id
                ),
            }
        )

        return self.feasibility_repository.create(
            result
        )
