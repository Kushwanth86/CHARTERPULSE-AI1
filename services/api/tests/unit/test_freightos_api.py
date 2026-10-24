
from fastapi.testclient import TestClient

from services.api.app.main import app
from services.api.app.api.routes.freightos import freightos_service
from services.api.app.services.freightos_service import FreightosNoQuoteError


client = TestClient(app)


def test_freightos_estimate_endpoint_returns_estimate(monkeypatch):
    expected = {
        "provider": "Freightos",
        "estimate_type": "CONTAINER_FREIGHT_ESTIMATE",
        "origin": "CNSHA",
        "destination": "USLGB",
        "loadtype": "container40",
        "quantity": 1,
        "price_min": 3262.0,
        "price_max": 3554.0,
        "currency": "USD",
        "transit_days_min": "17",
        "transit_days_max": "21",
        "mode": "FCL",
        "is_estimate": True,
        "source_url": "https://ship.freightos.com",
    }

    def fake_estimate(**kwargs):
        return expected

    monkeypatch.setattr(freightos_service, "estimate", fake_estimate)

    response = client.get(
        "/api/v1/freightos/estimate",
        params={
            "origin": "CNSHA",
            "destination": "USLGB",
        },
    )

    assert response.status_code == 200
    assert response.json() == expected


def test_freightos_estimate_endpoint_validates_quantity():
    response = client.get(
        "/api/v1/freightos/estimate",
        params={
            "origin": "CNSHA",
            "destination": "USLGB",
            "quantity": 0,
        },
    )

    assert response.status_code == 422



def test_freightos_no_quote_is_not_reported_as_gateway_failure(monkeypatch):
    def no_quote(**kwargs):
        raise FreightosNoQuoteError(
            "No freight quotes are available for this route and container type."
        )

    monkeypatch.setattr(freightos_service, "estimate", no_quote)

    response = client.get(
        "/api/v1/freightos/estimate",
        params={
            "origin": "BEANR",
            "destination": "USLGB",
            "loadtype": "container40",
            "quantity": 1,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "No freight quotes are available for this route and container type."
    )
