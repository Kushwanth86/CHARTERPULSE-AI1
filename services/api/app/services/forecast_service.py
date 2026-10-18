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

    def monthly_forecast(
        self,
        origin_location_id: UUID,
        destination_location_id: UUID,
        vessel_class: str,
        months: int = 12,
    ) -> list[dict]:
        """Generate month-end horizons from verified route/class observations only."""
        observations = self.market_repository.list(
            origin_location_id=origin_location_id,
            destination_location_id=destination_location_id,
            vessel_class=vessel_class.strip().upper(),
            limit=500,
        )
        verified = [
            row for row in observations
            if str(row.get("metric", "")).strip().upper() in {"FREIGHT_RATE", "OCEAN_FREIGHT"}
            and str(row.get("provenance", "")).upper()
            in {"REAL", "PUBLIC_PROXY", "USER_PROVIDED", "DERIVED"}
            and str(row.get("origin_location_id", "")) == str(origin_location_id)
            and str(row.get("destination_location_id", "")) == str(destination_location_id)
            and str(row.get("vessel_class", "")).strip().casefold() == vessel_class.strip().casefold()
        ]
        if not verified:
            raise ValueError(
                "No verified observations match this route and vessel class; "
                "monthly forecasts cannot be generated from simulated or unmatched data."
            )

        from datetime import datetime, timezone
        from calendar import monthrange

        parsed = []
        for row in verified:
            try:
                observed_at = datetime.fromisoformat(
                    str(row["observed_at"]).replace("Z", "+00:00")
                )
                parsed.append((observed_at, row))
            except (KeyError, TypeError, ValueError):
                continue
        if not parsed:
            raise ValueError("Matched observations do not contain valid observation dates.")
        latest = max(item[0] for item in parsed)
        results = []
        year, month = latest.year, latest.month
        for offset in range(1, months + 1):
            month_index = year * 12 + (month - 1) + offset
            target_year, month_zero = divmod(month_index, 12)
            target_month = month_zero + 1
            target_day = monthrange(target_year, target_month)[1]
            target = datetime(target_year, target_month, target_day, tzinfo=timezone.utc)
            horizon_days = max(1, (target - latest).days)
            forecast = self.engine.forecast(verified, horizon_days=horizon_days)
            results.append({
                "month": target.strftime("%Y-%m"),
                "target_date": target.date().isoformat(),
                "horizon_days": horizon_days,
                "p10": forecast["p10"],
                "p50": forecast["p50"],
                "p90": forecast["p90"],
                "unit": verified[-1].get("unit", "USD/MT"),
                "currency": verified[-1].get("currency", "USD"),
                "model_name": forecast["model_name"],
                "model_version": forecast["model_version"],
                "input_provenance": "VERIFIED_MATCHED_OBSERVATIONS",
                "observation_count": forecast["metadata"]["observation_count"],
            })
        return results

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
