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


REFERENCE_FREIGHT_OBSERVATIONS = [
    {
        "metric": "Panamax Freight Reference",
        "value": 28.4,
        "unit": "USD/MT",
        "currency": "USD",
        "observed_at": "2026-09-01T00:00:00Z",
    },
    {
        "metric": "Panamax Freight Reference",
        "value": 30.1,
        "unit": "USD/MT",
        "currency": "USD",
        "observed_at": "2026-09-05T00:00:00Z",
    },
    {
        "metric": "Panamax Freight Reference",
        "value": 31.5,
        "unit": "USD/MT",
        "currency": "USD",
        "observed_at": "2026-09-08T00:00:00Z",
    },
]


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

        provenance = "FORECAST"

        if not observations and (
            payload.origin_location_id
            or payload.destination_location_id
            or payload.vessel_class
        ):
            observations = self.market_repository.list(
                metric=payload.metric,
                limit=500,
            )
            provenance = "FORECAST_MARKET_REFERENCE"

        if not observations:
            observations = REFERENCE_FREIGHT_OBSERVATIONS
            provenance = "PUBLIC_PROXY_REFERENCE"

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
                "provenance": provenance,
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

        forecasts = self.forecast_repository.list(
            origin_location_id=origin_location_id,
            destination_location_id=destination_location_id,
            vessel_class=vessel_class,
            limit=limit,
        )

        if forecasts:
            return forecasts

        if origin_location_id or destination_location_id or vessel_class:
            try:
                generated = self.generate(
                    FreightForecastRequest(
                        origin_location_id=origin_location_id,
                        destination_location_id=destination_location_id,
                        vessel_class=vessel_class,
                        forecast_horizon_days=7,
                    )
                )
                return [generated]
            except ValueError:
                return []

        return forecasts
