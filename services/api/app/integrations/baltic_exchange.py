from __future__ import annotations

import json
import math
import os
import re
from datetime import date, datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from uuid import UUID


DEFAULT_API_BASE_URL = "https://api.balticexchange.com"
DEFAULT_API_VERSION = "v1.3"
SUPPORTED_USD_PER_METRIC_TON_UNITS = frozenset({"$/MT", "USD/MT"})


class BalticExchangeAPIError(RuntimeError):
    """Safe, user-facing error for Baltic Exchange API failures."""


class BalticExchangeClient:
    """Small standard-library client for Baltic Exchange's feed API.

    The API key is sent only in the x-apikey request header. It is never added
    to URLs, exception messages, or log output.
    """

    def __init__(
        self,
        api_key: str | None = None,
        feed_identifier: str | None = None,
        api_version: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float = 20.0,
    ) -> None:
        # Settings reads the repository-root .env as well as process environment.
        from services.api.app.config.settings import get_settings

        settings = get_settings()
        self.api_key = (
            api_key
            or os.getenv("BALTIC_EXCHANGE_API_KEY")
            or settings.baltic_exchange_api_key
            or ""
        ).strip()
        self.feed_identifier = (
            feed_identifier
            or os.getenv("BALTIC_EXCHANGE_FEED_ID")
            or settings.baltic_exchange_feed_id
            or ""
        ).strip()
        self.api_version = (
            api_version
            or os.getenv("BALTIC_EXCHANGE_API_VERSION")
            or settings.baltic_exchange_api_version
            or DEFAULT_API_VERSION
        ).strip()
        self.base_url = (
            base_url
            or os.getenv("BALTIC_EXCHANGE_API_BASE_URL")
            or settings.baltic_exchange_api_base_url
            or DEFAULT_API_BASE_URL
        ).rstrip("/")
        self.timeout_seconds = timeout_seconds

        if not self.api_key:
            raise ValueError("BALTIC_EXCHANGE_API_KEY is required.")
        if not self.feed_identifier:
            raise ValueError("BALTIC_EXCHANGE_FEED_ID is required.")
        if not re.fullmatch(r"v[0-9]+(?:\.[0-9]+)*", self.api_version):
            raise ValueError("BALTIC_EXCHANGE_API_VERSION must look like v1.3.")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", self.feed_identifier):
            raise ValueError("BALTIC_EXCHANGE_FEED_ID contains invalid characters.")
        if not self.base_url.startswith("https://"):
            raise ValueError("Baltic Exchange API base URL must use HTTPS.")

    def _get_json(self, endpoint: str, params: dict[str, str] | None = None) -> Any:
        safe_endpoint = endpoint.strip("/")
        url = (
            f"{self.base_url}/{self.api_version}/feed/"
            f"{quote(self.feed_identifier, safe='')}/{safe_endpoint}"
        )
        if params:
            url = f"{url}?{urlencode(params)}"
        request = Request(
            url,
            headers={"Accept": "application/json", "x-apikey": self.api_key},
            method="GET",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read()
        except HTTPError as exc:
            if exc.code == 401:
                reason = "Baltic Exchange rejected the API key or the account is not entitled to API access."
            elif exc.code == 404:
                reason = "Baltic Exchange could not find the feed/version identifier or access to a source may be restricted."
            elif exc.code == 429:
                reason = "Baltic Exchange rate limit reached. Wait before retrying."
            else:
                reason = f"Baltic Exchange returned HTTP {exc.code}."
            raise BalticExchangeAPIError(reason) from None
        except URLError:
            raise BalticExchangeAPIError(
                "Could not connect to Baltic Exchange. Check network access and try again."
            ) from None
        except TimeoutError:
            raise BalticExchangeAPIError("Baltic Exchange request timed out.") from None

        try:
            return json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise BalticExchangeAPIError(
                "Baltic Exchange returned a response that was not valid JSON."
            ) from None

    def latest_data_change(self) -> Any:
        """Return the feed's latest data-change marker.

        The provider recommends checking this marker before requesting feed
        data, avoiding repeated data calls when nothing has changed.
        """
        return self._get_json("latestDatumChangeOn")

    def get_feed_data(
        self,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> Any:
        params: dict[str, str] = {}
        for key, value in (("from", from_date), ("to", to_date)):
            if value:
                try:
                    date.fromisoformat(value)
                except ValueError as exc:
                    raise ValueError(f"{key}_date must use YYYY-MM-DD format.") from exc
                params[key] = value
        return self._get_json("data", params or None)


def load_route_mapping(raw_json: str) -> dict[str, dict[str, str]]:
    """Parse explicit provider-code to CharterPulse route mappings.

    Example:
      {"C5":{"origin_location_id":"<uuid>","destination_location_id":"<uuid>",
             "vessel_class":"Capesize"}}

    Mapping is deliberately explicit; provider benchmark descriptions are not
    used to guess a port-to-port route.
    """
    try:
        value = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError("BALTIC_EXCHANGE_ROUTE_MAP_JSON must be valid JSON.") from exc
    if not isinstance(value, dict) or not value:
        raise ValueError("BALTIC_EXCHANGE_ROUTE_MAP_JSON must be a non-empty JSON object.")

    normalized: dict[str, dict[str, str]] = {}
    for provider_code, entry in value.items():
        code = str(provider_code).strip()
        if not code or not isinstance(entry, dict):
            raise ValueError("Each route mapping must have a provider code and an object value.")
        try:
            origin_id = str(UUID(str(entry.get("origin_location_id", ""))))
            destination_id = str(UUID(str(entry.get("destination_location_id", ""))))
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError(
                f"Route mapping {code!r} must contain valid origin and destination UUIDs."
            ) from exc
        if origin_id == destination_id:
            raise ValueError(f"Route mapping {code!r} must use distinct locations.")
        vessel_class = str(entry.get("vessel_class") or "").strip()
        if not vessel_class:
            raise ValueError(f"Route mapping {code!r} must specify vessel_class.")
        normalized[code] = {
            "origin_location_id": origin_id,
            "destination_location_id": destination_id,
            "vessel_class": vessel_class,
        }
    return normalized


def _unit_is_usd_per_metric_ton(value: Any) -> bool:
    normalized = str(value or "").strip().upper().replace(" ", "")
    return normalized in SUPPORTED_USD_PER_METRIC_TON_UNITS


def _parse_observation_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = datetime.combine(date.fromisoformat(text), datetime.min.time())
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    else:
        parsed = parsed.astimezone(timezone.utc)
    return parsed


def parse_feed_observations(
    feed_payload: Any,
    route_mapping: dict[str, dict[str, str]],
) -> dict[str, Any]:
    """Convert documented Baltic feed JSON into validated market-observation rows.

    Only USD-per-metric-tonne indices with explicit route mappings are eligible.
    Other units (for example USD/day), unmapped codes, malformed dates, and
    non-positive/non-finite values are skipped rather than coerced.
    """
    if not isinstance(feed_payload, list):
        raise ValueError("Baltic feed data must be a JSON array.")

    observations_by_reference: dict[str, dict[str, Any]] = {}
    skipped = {
        "unmapped_source": 0,
        "unsupported_unit": 0,
        "invalid_point": 0,
        "duplicate_point": 0,
    }

    for series in feed_payload:
        if not isinstance(series, dict):
            skipped["invalid_point"] += 1
            continue
        source_code = str(series.get("id") or series.get("shortCode") or "").strip()
        short_code = str(series.get("shortCode") or "").strip()
        mapping = route_mapping.get(source_code) or route_mapping.get(short_code)
        if not mapping:
            skipped["unmapped_source"] += 1
            continue
        if not _unit_is_usd_per_metric_ton(series.get("datumUnit")):
            skipped["unsupported_unit"] += 1
            continue

        points = series.get("data")
        if not isinstance(points, list):
            skipped["invalid_point"] += 1
            continue

        label = str(series.get("shortDescription") or source_code).strip()
        for point in points:
            if not isinstance(point, dict):
                skipped["invalid_point"] += 1
                continue
            try:
                numeric_value = float(point.get("value"))
            except (TypeError, ValueError, OverflowError):
                skipped["invalid_point"] += 1
                continue
            observed_at = _parse_observation_time(point.get("date"))
            if not math.isfinite(numeric_value) or numeric_value <= 0 or observed_at is None:
                skipped["invalid_point"] += 1
                continue

            observation_date = observed_at.date().isoformat()
            source_reference = f"baltic-exchange:{source_code}:{observation_date}"
            if source_reference in observations_by_reference:
                skipped["duplicate_point"] += 1
                continue
            observations_by_reference[source_reference] = {
                "market_type": "FREIGHT",
                "metric": "OCEAN_FREIGHT",
                "origin_location_id": mapping["origin_location_id"],
                "destination_location_id": mapping["destination_location_id"],
                "vessel_class": mapping["vessel_class"],
                "value": numeric_value,
                "unit": "USD/MT",
                "currency": "USD",
                "observed_at": observed_at.isoformat(),
                "source": f"Baltic Exchange: {label}",
                "source_reference": source_reference,
                "provenance": "REAL",
            }

    return {"observations": list(observations_by_reference.values()), "skipped": skipped}
