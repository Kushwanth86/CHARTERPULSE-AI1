from uuid import UUID

from services.api.app.repositories.market_repository import MarketRepository
from services.api.app.schemas.market import MarketObservationCreate


class MarketService:
    def __init__(self):
        self.repository = MarketRepository()

    def create(self, payload: MarketObservationCreate, user_id: UUID) -> dict:
        data = payload.model_dump(mode="json")
        # A caller cannot self-assert provider provenance. The owner is assigned
        # from the authenticated token and trusted provider imports remain a
        # separate server-side ingestion boundary.
        data["provenance"] = "USER_PROVIDED"
        return self.repository.create(data, user_id)

    def list(
        self,
        user_id: UUID,
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
            user_id=user_id,
        )
