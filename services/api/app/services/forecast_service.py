from __future__ import annotations

from datetime import datetime, timezone
from math import isfinite
from typing import Any
from uuid import UUID

from services.api.app.intelligence.freight_forecast import FreightForecastEngine
from services.api.app.repositories.forecast_repository import ForecastRepository
from services.api.app.repositories.market_repository import MarketRepository
from services.api.app.schemas.forecasts import FreightForecastRequest
from services.api.app.services.forecast_evidence import (
    assert_decision_eligible_forecast,
)


ALLOWED_SOURCE_PROVENANCES = frozenset({"REAL", "PUBLIC_PROXY"})
OCEAN_FREIGHT_METRICS = frozenset(
    {"FREIGHT_RATE", "OCEAN_FREIGHT", "OCEAN_FREIGHT_RATE"}
)


def _canonical_metric(value: Any) -> str:
    normalized = str(value or "").strip().upper()
    return "OCEAN_FREIGHT" if normalized in OCEAN_FREIGHT_METRICS else normalized


def _parse_observation_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _finite_positive(value: Any) -> bool:
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return False
    return isfinite(parsed) and parsed > 0


class ForecastService:
    def __init__(self):
        self.market_repository = MarketRepository()
        self.forecast_repository = ForecastRepository()
        self.engine = FreightForecastEngine()

    def generate(self, payload: FreightForecastRequest) -> dict:
        has_origin = payload.origin_location_id is not None
        has_destination = payload.destination_location_id is not None
        has_vessel_class = bool(str(payload.vessel_class or "").strip())
        route_scoped = has_origin and has_destination

        # One endpoint alone is never a valid route. A vessel-class-only query
        # may return an aggregate market report, but evidence metadata marks it
        # unscoped so it cannot be selected for a procurement decision.
        if has_origin != has_destination:
            raise ValueError(
                "A route-specific forecast requires both origin and destination location IDs."
            )

        requested_metric = _canonical_metric(payload.metric)
        if requested_metric == "OCEAN_FREIGHT":
            raw_observations = self.market_repository.list(
                metric=None,
                origin_location_id=payload.origin_location_id,
                destination_location_id=payload.destination_location_id,
                vessel_class=payload.vessel_class,
                limit=500,
            )
            raw_observations = [
                row for row in raw_observations
                if _canonical_metric(row.get("metric")) == requested_metric
            ]
        else:
            raw_observations = self.market_repository.list(
                metric=payload.metric,
                origin_location_id=payload.origin_location_id,
                destination_location_id=payload.destination_location_id,
                vessel_class=payload.vessel_class,
                limit=500,
            )

        observations = []
        saw_simulated_observation = False
        for row in raw_observations:
            source_provenance = str(row.get("provenance") or "").strip().upper()
            if source_provenance == "SIMULATED":
                saw_simulated_observation = True
            if source_provenance not in ALLOWED_SOURCE_PROVENANCES:
                continue

            if str(row.get("unit") or "").strip().upper().replace(" ", "") != (
                str(payload.unit or "").strip().upper().replace(" ", "")
            ):
                continue

            row_currency = str(row.get("currency") or "").strip().upper()
            requested_currency = str(payload.currency or "").strip().upper()
            if row_currency and requested_currency and row_currency != requested_currency:
                continue

            if not _finite_positive(row.get("value")):
                continue

            timestamp = _parse_observation_time(row.get("observed_at"))
            if timestamp is None:
                continue

            # If the procurement did not specify a vessel class, do not blend
            # observations explicitly labelled for different vessel classes.
            row_class = str(row.get("vessel_class") or "").strip().casefold() or None
            requested_class = str(payload.vessel_class or "").strip().casefold() or None
            if row_class != requested_class:
                continue

            observations.append(row)

        if not observations:
            if saw_simulated_observation:
                raise ValueError(
                    "No eligible non-simulated market observations matched: only simulated test data "
                    "matched the requested market series. Simulated observations are excluded "
                    "from freight forecasts."
                )
            raise ValueError(
                "No verified market observations match this metric, route or vessel class, and unit. "
                "Static reference values are not substituted."
            )

        # Repositories fetch the newest N rows for a bounded query, but both
        # the trend engine and chronological holdout backtest must see a
        # stable oldest-to-newest sequence.
        observations.sort(
            key=lambda row: _parse_observation_time(row.get("observed_at"))
            or datetime.min.replace(tzinfo=timezone.utc)
        )

        observed_dates = {
            _parse_observation_time(row.get("observed_at")).date().isoformat()
            for row in observations
            if _parse_observation_time(row.get("observed_at")) is not None
        }

        if route_scoped and len(observed_dates) < 3:
            raise ValueError(
                "A route-specific forecast requires at least three eligible observations from distinct dates. "
                "A single report or a generic benchmark is not enough."
            )

        result = self.engine.forecast(
            observations=observations,
            horizon_days=payload.forecast_horizon_days,
        )

        metadata = dict(result.get("metadata") or {})
        metadata.update(
            {
                "input_provenance": "MARKET_OBSERVATION",
                "source_provenances": sorted(
                    {
                        str(row.get("provenance") or "").strip().upper()
                        for row in observations
                    }
                ),
                "source_labels": sorted(
                    {
                        str(row.get("source") or "").strip()
                        for row in observations
                        if str(row.get("source") or "").strip()
                    }
                ),
                "source_references": sorted(
                    {
                        str(row.get("source_reference") or "").strip()
                        for row in observations
                        if str(row.get("source_reference") or "").strip()
                    }
                ),
                "route_scoped": bool(route_scoped),
                "distinct_observation_dates": len(observed_dates),
                "eligible_observation_count": len(observations),
                "evidence_status": (
                    "ROUTE_SCOPED_OBSERVATIONS"
                    if route_scoped
                    else "AGGREGATE_OBSERVATIONS"
                ),
            }
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
                "forecast_horizon_days": payload.forecast_horizon_days,
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
        has_origin = origin_location_id is not None
        has_destination = destination_location_id is not None
        has_vessel_class = bool(str(vessel_class or "").strip())
        route_scoped = has_origin and has_destination
        scoped_request = has_origin or has_destination or has_vessel_class

        forecasts = self.forecast_repository.list(
            origin_location_id=origin_location_id,
            destination_location_id=destination_location_id,
            vessel_class=vessel_class,
            limit=limit,
        )

        # Exclude legacy demo/proxy rows even if their UUIDs happen to match.
        eligible_forecasts = []
        for forecast in forecasts:
            try:
                assert_decision_eligible_forecast(forecast)
            except ValueError:
                continue

            if scoped_request and not route_scoped:
                continue
            if route_scoped and (
                str(forecast.get("origin_location_id") or "") != str(origin_location_id)
                or str(forecast.get("destination_location_id") or "") != str(destination_location_id)
            ):
                continue

            forecast_class = str(forecast.get("vessel_class") or "").strip().casefold() or None
            requested_class = str(vessel_class or "").strip().casefold() or None
            if forecast_class != requested_class:
                continue

            eligible_forecasts.append(forecast)

        if eligible_forecasts:
            return eligible_forecasts

        if route_scoped:
            try:
                generated = self.generate(
                    FreightForecastRequest(
                        origin_location_id=origin_location_id,
                        destination_location_id=destination_location_id,
                        vessel_class=vessel_class,
                        forecast_horizon_days=7,
                        metric="OCEAN_FREIGHT",
                        unit="USD/MT",
                        currency="USD",
                    )
                )
                assert_decision_eligible_forecast(generated)
                return [generated]
            except ValueError:
                return []

        # Do not invent an unscoped reference forecast when the API has no
        # eligible source observations.
        return []
