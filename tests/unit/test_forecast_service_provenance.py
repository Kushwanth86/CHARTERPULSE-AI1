
from services.api.app.schemas.forecasts import FreightForecastRequest
from services.api.app.services import forecast_service


def test_reference_forecast_preserves_input_provenance(monkeypatch):
    class EmptyMarketRepository:
        def list(self, **kwargs):
            return []

    class RecordingForecastRepository:
        def __init__(self):
            self.payload = None

        def create(self, payload):
            self.payload = payload
            return payload

    repository = RecordingForecastRepository()

    monkeypatch.setattr(
        forecast_service,
        "MarketRepository",
        EmptyMarketRepository,
    )
    monkeypatch.setattr(
        forecast_service,
        "ForecastRepository",
        lambda: repository,
    )

    service = forecast_service.ForecastService()
    service.generate(FreightForecastRequest())

    # The record is a forecast, while metadata identifies its input source.
    assert repository.payload["provenance"] == "FORECAST"
    assert (
        repository.payload["metadata"]["input_provenance"]
        == "SIMULATED_REFERENCE"
    )

    # The restored implementation does not add this metadata field.
    assert (
        "route_specific_observations"
        not in repository.payload["metadata"]
    )

def test_scoped_forecast_does_not_fall_back_to_unmatched_market_data(monkeypatch):
    class EmptyScopedMarketRepository:
        def __init__(self):
            self.calls = []

        def list(self, **kwargs):
            self.calls.append(kwargs)
            return []

    class ForbiddenForecastRepository:
        def create(self, payload):
            raise AssertionError("A forecast must not be stored without matched observations.")

    market = EmptyScopedMarketRepository()
    monkeypatch.setattr(forecast_service, "MarketRepository", lambda: market)
    monkeypatch.setattr(
        forecast_service,
        "ForecastRepository",
        ForbiddenForecastRepository,
    )

    service = forecast_service.ForecastService()
    request = FreightForecastRequest(
        origin_location_id="00000000-0000-0000-0000-000000000001",
        destination_location_id="00000000-0000-0000-0000-000000000002",
        vessel_class="Panamax",
    )

    try:
        service.generate(request)
    except ValueError as exc:
        assert "No market observations match" in str(exc)
    else:
        raise AssertionError("Expected a scoped forecast request to fail closed.")

    assert len(market.calls) == 1
    assert market.calls[0]["vessel_class"] == "Panamax"


def test_scoped_forecast_rejects_simulated_market_observations(monkeypatch):
    class SimulatedMarketRepository:
        def list(self, **kwargs):
            return [
                {
                    "metric": "OCEAN_FREIGHT",
                    "value": 30.0,
                    "unit": "USD/MT",
                    "vessel_class": "PANAMAX",
                    "provenance": "SIMULATED",
                    "origin_location_id": None,
                    "destination_location_id": None,
                    "observed_at": "2026-09-05T00:00:00Z",
                }
            ]

    class ForbiddenForecastRepository:
        def create(self, payload):
            raise AssertionError("Simulated data must not create a scoped forecast.")

    monkeypatch.setattr(
        forecast_service, "MarketRepository", SimulatedMarketRepository
    )
    monkeypatch.setattr(
        forecast_service, "ForecastRepository", ForbiddenForecastRepository
    )

    service = forecast_service.ForecastService()
    request = FreightForecastRequest(vessel_class="PANAMAX")

    try:
        service.generate(request)
    except ValueError as exc:
        assert "simulated test data" in str(exc)
    else:
        raise AssertionError("Expected simulated observations to be rejected.")
