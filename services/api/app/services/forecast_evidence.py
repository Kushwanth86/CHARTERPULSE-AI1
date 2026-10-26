from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from math import isfinite
from typing import Any


ALLOWED_SOURCE_PROVENANCES = frozenset({"REAL", "PUBLIC_PROXY"})


def _decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _normalized_class(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return "__INVALID_CLASS__"
    normalized = value.strip().casefold()
    return normalized or None


def decision_forecast_error(forecast: dict[str, Any]) -> str | None:
    """Return why a stored forecast cannot drive a procurement decision."""
    if str(forecast.get("provenance") or "").strip().upper() != "FORECAST":
        return "This forecast is a proxy or demo reference, not an eligible forecast."

    origin_id = forecast.get("origin_location_id")
    destination_id = forecast.get("destination_location_id")
    if not origin_id or not destination_id or str(origin_id) == str(destination_id):
        return "A decision requires an exact, distinct origin and destination."

    if str(forecast.get("unit") or "").strip().upper().replace(" ", "") != "USD/MT":
        return "The current decision engine only supports freight rates in USD/MT."

    metadata = forecast.get("metadata")
    if not isinstance(metadata, dict):
        return "Forecast evidence metadata is missing."

    if metadata.get("route_scoped") is not True:
        return "An aggregate or unscoped forecast cannot drive a route decision."

    if str(metadata.get("input_provenance") or "").strip().upper() != "MARKET_OBSERVATION":
        return "The forecast was not generated from market observations."

    count = metadata.get("observation_count")
    distinct_dates = metadata.get("distinct_observation_dates")
    if (
        isinstance(count, bool)
        or not isinstance(count, (int, float))
        or not isfinite(float(count))
        or int(count) != count
        or count < 3
        or isinstance(distinct_dates, bool)
        or not isinstance(distinct_dates, (int, float))
        or not isfinite(float(distinct_dates))
        or int(distinct_dates) != distinct_dates
        or distinct_dates < 3
    ):
        return "At least three observations from distinct dates are required."

    source_labels = metadata.get("source_labels")
    if (
        not isinstance(source_labels, list)
        or not source_labels
        or not all(isinstance(label, str) and label.strip() for label in source_labels)
    ):
        return "Traceable source labels are missing from the forecast evidence."

    source_provenances = metadata.get("source_provenances")
    if not isinstance(source_provenances, list) or not source_provenances:
        return "Source provenance is missing from the forecast evidence."
    normalized_sources = {
        str(source or "").strip().upper()
        for source in source_provenances
    }
    if not normalized_sources or not normalized_sources.issubset(ALLOWED_SOURCE_PROVENANCES):
        return "Simulated, user-entered, or unknown provenance cannot drive a decision."

    quantiles = [_decimal(forecast.get(key)) for key in ("p10", "p50", "p90")]
    if any(value is None for value in quantiles):
        return "Forecast quantiles must be finite numeric values."
    p10, p50, p90 = quantiles
    assert p10 is not None and p50 is not None and p90 is not None
    if p10 < 0 or p50 <= 0 or p90 <= 0 or not (p10 <= p50 <= p90):
        return "Forecast quantiles must be non-negative, finite, and ordered P10 ≤ P50 ≤ P90."

    generated_at = forecast.get("generated_at")
    if not isinstance(generated_at, str) or not generated_at.strip():
        return "The forecast generation timestamp is missing."
    try:
        datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    except ValueError:
        return "The forecast generation timestamp is invalid."

    return None


def assert_decision_eligible_forecast(forecast: dict[str, Any]) -> None:
    reason = decision_forecast_error(forecast)
    if reason:
        raise ValueError(reason)


def assert_cargo_matches_forecast(
    cargo: dict[str, Any],
    forecast: dict[str, Any],
    requested_quantity_mt: Any,
) -> None:
    """Bind a decision to the saved cargo requirement and its exact route/class."""
    actual_quantity = _decimal(cargo.get("quantity_mt"))
    requested_quantity = _decimal(requested_quantity_mt)
    if (
        actual_quantity is None
        or requested_quantity is None
        or actual_quantity <= 0
        or requested_quantity <= 0
    ):
        raise ValueError("Cargo quantity must be a finite positive metric-tonne value.")
    if actual_quantity != requested_quantity:
        raise ValueError(
            "The requested quantity does not match the saved procurement requirement."
        )

    for field in ("origin_location_id", "destination_location_id"):
        cargo_value = cargo.get(field)
        forecast_value = forecast.get(field)
        if not cargo_value or not forecast_value or str(cargo_value) != str(forecast_value):
            raise ValueError(
                "The selected freight forecast does not match the saved procurement route."
            )

    cargo_class = _normalized_class(cargo.get("vessel_class"))
    forecast_class = _normalized_class(forecast.get("vessel_class"))
    if cargo_class == "__INVALID_CLASS__" or forecast_class == "__INVALID_CLASS__":
        raise ValueError("Vessel class must be a string or null.")
    if cargo_class != forecast_class:
        raise ValueError(
            "The selected freight forecast does not match the saved procurement vessel class."
        )
