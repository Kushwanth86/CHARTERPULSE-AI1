from uuid import UUID

from services.api.app.repositories.market_repository import (
    MarketRepository,
)
from services.api.app.schemas.market import (
    MarketObservationCreate,
)


class MarketService:

    def __init__(self):
        self.repository = MarketRepository()

    def create(
        self,
        payload: MarketObservationCreate,
    ) -> dict:

        return self.repository.create(
            payload.model_dump(mode="json")
        )

    def list(
        self,
        metric: str | None = None,
        origin_location_id: UUID | None = None,
        destination_location_id: UUID | None = None,
        vessel_class: str | None = None,
        limit: int = 500,
    ) -> list[dict]:

        return self.repository.list(
            metric=metric,
            origin_location_id=origin_location_id,
            destination_location_id=destination_location_id,
            vessel_class=vessel_class,
            limit=limit,
        )
