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

    assert repository.payload["provenance"] == "PUBLIC_PROXY_REFERENCE"
    assert repository.payload["metadata"]["input_provenance"] == "PUBLIC_PROXY_REFERENCE"
    assert repository.payload["metadata"]["route_specific_observations"] is False
