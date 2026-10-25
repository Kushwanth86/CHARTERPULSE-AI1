
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
        assert "No verified market observations match" in str(exc)
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


def source_rows(**overrides):
    base = [
        {
            "metric": "freight_rate",
            "value": 29.5,
            "unit": "USD/MT",
            "currency": "USD",
            "vessel_class": "Panamax",
            "provenance": "REAL",
            "source": "Licensed Freight Provider",
            "source_record_id": "quote-001",
            "source_reference": "https://provider.example/quote/quote-001",
            "observed_at": "2026-10-20T12:00:00Z",
            "retrieved_at": "2026-10-25T09:30:00Z",
        },
        {
            "metric": "freight_rate",
            "value": 30.0,
            "unit": "USD/MT",
            "currency": "USD",
            "vessel_class": "PANAMAX",
            "provenance": "REAL",
            "source": "Licensed Freight Provider",
            "source_record_id": "quote-002",
            "source_reference": "https://provider.example/quote/quote-002",
            "observed_at": "2026-10-21T12:00:00Z",
            "retrieved_at": "2026-10-25T09:30:00Z",
        },
        {
            "metric": "freight_rate",
            "value": 30.25,
            "unit": "USD/MT",
            "currency": "USD",
            "vessel_class": "Panamax",
            "provenance": "REAL",
            "source": "Licensed Freight Provider",
            "source_record_id": "quote-003",
            "source_reference": "https://provider.example/quote/quote-003",
            "observed_at": "2026-10-22T12:00:00Z",
            "retrieved_at": "2026-10-25T09:30:00Z",
        },
    ]
    return [{**row, **overrides.get(str(index), {})} for index, row in enumerate(base)]


def test_source_observation_forecast_preserves_input_lineage(monkeypatch):
    class SourceMarketRepository:
        def list(self, **kwargs):
            return source_rows()

    class RecordingForecastRepository:
        def __init__(self):
            self.payload = None

        def create(self, payload):
            self.payload = payload
            return payload

    repository = RecordingForecastRepository()
    monkeypatch.setattr(
        forecast_service, "MarketRepository", SourceMarketRepository
    )
    monkeypatch.setattr(
        forecast_service, "ForecastRepository", lambda: repository
    )

    result = forecast_service.ForecastService().generate(
        FreightForecastRequest(
            origin_location_id="00000000-0000-0000-0000-000000000001",
            destination_location_id="00000000-0000-0000-0000-000000000002",
            vessel_class="Panamax",
        )
    )

    metadata = result["metadata"]
    assert result["provenance"] == "FORECAST"
    assert metadata["input_provenance"] == "MARKET_OBSERVATION"
    assert metadata["input_observation_count"] == 3
    assert metadata["input_observation_provenance"] == ["REAL"]
    assert metadata["input_sources"] == ["Licensed Freight Provider"]
    assert metadata["input_source_record_ids"] == [
        "quote-001",
        "quote-002",
        "quote-003",
    ]
    assert len(metadata["input_source_references"]) == 3
    assert metadata["input_unit"] == "USD/MT"
    assert metadata["input_currency"] == "USD"


def test_source_observation_forecast_rejects_mixed_or_incompatible_units(monkeypatch):
    class WrongUnitRepository:
        def list(self, **kwargs):
            rows = source_rows()
            rows[0]["unit"] = "USD/day"
            return rows

    class ForbiddenForecastRepository:
        def create(self, payload):
            raise AssertionError("Forecast must not be stored for incompatible units.")

    monkeypatch.setattr(
        forecast_service, "MarketRepository", WrongUnitRepository
    )
    monkeypatch.setattr(
        forecast_service, "ForecastRepository", ForbiddenForecastRepository
    )

    request = FreightForecastRequest(
        origin_location_id="00000000-0000-0000-0000-000000000001",
        destination_location_id="00000000-0000-0000-0000-000000000002",
        vessel_class="Panamax",
    )

    try:
        forecast_service.ForecastService().generate(request)
    except ValueError as exc:
        assert "Freight observations must use USD/MT and USD" in str(exc)
    else:
        raise AssertionError("Expected incompatible freight units to be rejected.")


def test_forecast_derived_rows_cannot_be_reused_as_market_inputs(monkeypatch):
    class ForecastDerivedMarketRepository:
        def list(self, **kwargs):
            rows = source_rows()
            rows[0]["provenance"] = "FORECAST"
            return rows

    class ForbiddenForecastRepository:
        def create(self, payload):
            raise AssertionError("Forecast-derived observations must not be used.")

    monkeypatch.setattr(
        forecast_service, "MarketRepository", ForecastDerivedMarketRepository
    )
    monkeypatch.setattr(
        forecast_service, "ForecastRepository", ForbiddenForecastRepository
    )

    request = FreightForecastRequest(
        origin_location_id="00000000-0000-0000-0000-000000000001",
        destination_location_id="00000000-0000-0000-0000-000000000002",
        vessel_class="Panamax",
    )

    try:
        forecast_service.ForecastService().generate(request)
    except ValueError as exc:
        assert "Forecast-derived records cannot be reused" in str(exc)
    else:
        raise AssertionError("Expected forecast-derived inputs to be rejected.")
