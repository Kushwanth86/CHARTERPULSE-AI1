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

        data = payload.model_dump(mode="json")

        # This endpoint is caller-facing, not a trusted provider ingestion
        # boundary. Never accept REAL/PUBLIC_PROXY as proof merely because a
        # caller supplied that string. Trusted provider adapters should write
        # through a server-side ingestion path with independently established
        # source provenance.
        data["provenance"] = "USER_PROVIDED"
        return self.repository.create(data)

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
