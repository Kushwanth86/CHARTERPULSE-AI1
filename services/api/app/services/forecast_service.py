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

        scoped_request = bool(
            payload.origin_location_id
            or payload.destination_location_id
            or payload.vessel_class
        )

        # Simulated scenario rows are useful for demos, never for real procurement
        # decisions. Do not let them masquerade as observed market prices.
        simulated = [
            row for row in observations
            if str(row.get("provenance", "")).upper() == "SIMULATED"
        ]
        observations = [
            row for row in observations
            if str(row.get("provenance", "")).upper() != "SIMULATED"
        ]

        if scoped_request and simulated:
            raise ValueError(
                "Matching records are simulated test data, not verified market "
                "observations. A route/class-specific forecast requires verified "
                "market data."
            )

        input_provenance = "MARKET_OBSERVATION"

        # Never label broad-market or proxy observations as route/class-specific.
        if not observations and scoped_request:
            raise ValueError(
                "No verified market observations match the requested route and "
                "vessel class. A route-specific forecast cannot be generated "
                "until matching data is available."
            )

        if not observations:
            observations = REFERENCE_FREIGHT_OBSERVATIONS
            input_provenance = "SIMULATED_REFERENCE"

        result = self.engine.forecast(
            observations=observations,
            horizon_days=payload.forecast_horizon_days,
        )

        metadata = dict(result.get("metadata") or {})
        metadata["input_provenance"] = input_provenance

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
                "provenance": "FORECAST",
                "metadata": metadata,
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
