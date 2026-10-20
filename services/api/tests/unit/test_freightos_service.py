
import json
from unittest.mock import MagicMock, patch

import pytest

from services.api.app.services.freightos_service import (
    FreightosService,
    FreightosServiceError,
)


@pytest.fixture
def service():
    return FreightosService()


def mock_response(payload):
    response = MagicMock()
    response.__enter__.return_value.read.return_value = (
        json.dumps(payload).encode("utf-8")
    )
    return response


def test_estimate_returns_container_price_range(service):
    payload = {
        "response": {
            "estimatedFreightRates": {
                "mode": {
                    "price": {
                        "min": {
                            "moneyAmount": {
                                "amount": "3262",
                                "currency": "USD",
                            }
                        },
                        "max": {
                            "moneyAmount": {
                                "amount": "3554",
                                "currency": "USD",
                            }
                        },
                    },
                    "transitTimes": {
                        "min": "17",
                        "max": "21",
                        "unit": "days",
                    },
                    "mode": "FCL",
                }
            }
        }
    }

    with patch(
        "services.api.app.services.freightos_service.urlopen",
        return_value=mock_response(payload),
    ):
        result = service.estimate(
            origin="CNSHA",
            destination="USLGB",
        )

    assert result["provider"] == "Freightos"
    assert result["estimate_type"] == "CONTAINER_FREIGHT_ESTIMATE"
    assert result["price_min"] == 3262.0
    assert result["price_max"] == 3554.0
    assert result["currency"] == "USD"
    assert result["transit_days_min"] == "17"
    assert result["transit_days_max"] == "21"


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
    payload = {"response": {}}

    with patch(
        "services.api.app.services.freightos_service.urlopen",
        return_value=mock_response(payload),
    ):
        with pytest.raises(FreightosServiceError):
            service.estimate(
                origin="CNSHA",
                destination="USLGB",
            )
