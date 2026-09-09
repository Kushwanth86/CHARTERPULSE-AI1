from uuid import UUID

from services.api.app.intelligence.freight_forecast import (
    FreightForecastEngine,
)
from services.api.app.repositories.forecast_repository import (
    ForecastRepository,
)
from services.api.app.repositories.market_repository import (
    MarketRepository,
)
from services.api.app.schemas.forecasts import (
    FreightForecastRequest,
)


class ForecastService:

    def __init__(self):
        self.market_repository = MarketRepository()
        self.forecast_repository = ForecastRepository()
        self.engine = FreightForecastEngine()

    def generate(
        self,
        payload: FreightForecastRequest,
    ) -> dict:

        observations = self.market_repository.list(
            metric=payload.metric,
            origin_location_id=payload.origin_location_id,
            destination_location_id=payload.destination_location_id,
            vessel_class=payload.vessel_class,
            limit=500,
        )

        result = self.engine.forecast(
            observations=observations,
            horizon_days=payload.forecast_horizon_days,
        )

        result.update(
            {
                "origin_location_id": (
                    str(payload.origin_location_id)
                    if payload.origin_location_id
                    else None
                ),
                "destination_location_id": (
                    str(payload.destination_location_id)
                    if payload.destination_location_id
                    else None
                ),
                "vessel_class": payload.vessel_class,
                "forecast_horizon_days": (
                    payload.forecast_horizon_days
                ),
                "unit": payload.unit,
                "currency": payload.currency,
            }
        )

        return self.forecast_repository.create(result)

    def list(
        self,
        origin_location_id: UUID | None = None,
        destination_location_id: UUID | None = None,
        vessel_class: str | None = None,
        limit: int = 100,
    ) -> list[dict]:

        return self.forecast_repository.list(
            origin_location_id=origin_location_id,
            destination_location_id=destination_location_id,
            vessel_class=vessel_class,
            limit=limit,
        )
