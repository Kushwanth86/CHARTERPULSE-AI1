import json
from urllib.error import HTTPError
from unittest.mock import MagicMock, patch

import pytest

from services.api.app.services import freightos_service as freightos_module
from services.api.app.services.freightos_service import (
    _CACHE_LOCK,
    _ESTIMATE_CACHE,
    FreightosRateLimitError,
    FreightosService,
    FreightosServiceError,
)


@pytest.fixture(autouse=True)
def clear_estimate_cache():
    # Isolate process-local cache and cooldown state between tests.
    with _CACHE_LOCK:
        _ESTIMATE_CACHE.clear()
        freightos_module._RATE_LIMIT_UNTIL = 0.0


@pytest.fixture
def service():
    return FreightosService()


def mock_response(payload):
    response = MagicMock()
    response.__enter__.return_value.read.return_value = (
        json.dumps(payload).encode("utf-8")
    )
    return response


def valid_payload():
    return {
        "response": {
            "estimatedFreightRates": {
                "numQuotes": 1,
                "mode": {
                    "price": {
                        "min": {"moneyAmount": {"amount": "3262", "currency": "USD"}},
                        "max": {"moneyAmount": {"amount": "3554", "currency": "USD"}},
                    },
                    "transitTimes": {"min": "17", "max": "21", "unit": "days"},
                    "mode": "FCL",
                },
            }
        }
    }


def test_estimate_returns_container_price_range(service):
    with patch(
        "services.api.app.services.freightos_service.urlopen",
        return_value=mock_response(valid_payload()),
    ):
        result = service.estimate(origin="CNSHA", destination="USLGB")

    assert result["provider"] == "Freightos"
    assert result["estimate_type"] == "CONTAINER_FREIGHT_ESTIMATE"
    assert result["price_min"] == 3262.0
    assert result["price_max"] == 3554.0
    assert result["currency"] == "USD"
    assert result["transit_days_min"] == "17"
    assert result["transit_days_max"] == "21"


def test_estimate_reports_no_quotes_without_a_price(service):
    payload = {"response": {"estimatedFreightRates": {"numQuotes": 0}}}
    with patch(
        "services.api.app.services.freightos_service.urlopen",
        return_value=mock_response(payload),
    ):
        with pytest.raises(FreightosServiceError, match="No freight quotes are available"):
            service.estimate(
                origin="CNSZX",
                destination="KRPUS",
                loadtype="container45",
            )


def test_estimate_surfaces_retry_after_and_pauses_other_routes(service):
    error = HTTPError(
        "https://ship.freightos.com/api/shippingCalculator",
        429,
        "Too Many Requests",
        {"Retry-After": "45"},
        None,
    )
    with patch(
        "services.api.app.services.freightos_service.urlopen",
        side_effect=error,
    ) as mocked_urlopen:
        with pytest.raises(FreightosRateLimitError) as exc_info:
            service.estimate(
                origin="CNHKG",
                destination="AUSYD",
                loadtype="container20",
            )
        with pytest.raises(FreightosRateLimitError):
            service.estimate(
                origin="CNSHA",
                destination="USLGB",
                loadtype="container40",
            )

    assert exc_info.value.retry_after == 45
    assert "rate-limiting" in str(exc_info.value)
    mocked_urlopen.assert_called_once()


def test_estimate_caches_successful_results_for_identical_requests(service):
    with patch(
        "services.api.app.services.freightos_service.urlopen",
        return_value=mock_response(valid_payload()),
    ) as mocked_urlopen:
        first = service.estimate(
            origin="BRSSZ",
            destination="GBFXT",
            loadtype="container40HC",
        )
        second = service.estimate(
            origin="BRSSZ",
            destination="GBFXT",
            loadtype="container40HC",
        )

    assert first == second
    mocked_urlopen.assert_called_once()


def test_estimate_rejects_unsupported_container_type(service):
    with pytest.raises(ValueError, match="Unsupported container"):
        service.estimate(
            origin="CNSHA",
            destination="USLGB",
            loadtype="panamax",
        )


def test_estimate_rejects_invalid_quantity(service):
    with pytest.raises(ValueError, match="Quantity"):
        service.estimate(
            origin="CNSHA",
            destination="USLGB",
            quantity=0,
        )


def test_estimate_handles_missing_freight_rates(service):
    with patch(
        "services.api.app.services.freightos_service.urlopen",
        return_value=mock_response({"response": {}}),
    ):
        with pytest.raises(FreightosServiceError):
            service.estimate(origin="CNSHA", destination="USLGB")
