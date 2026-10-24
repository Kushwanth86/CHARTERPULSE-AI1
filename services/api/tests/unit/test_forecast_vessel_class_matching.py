from types import SimpleNamespace
from uuid import uuid4

from services.api.app.repositories.forecast_repository import ForecastRepository
from services.api.app.repositories.market_repository import MarketRepository


class FakeQuery:
    def __init__(self):
        self.filters = []

    def select(self, *args, **kwargs):
        return self

    def eq(self, column, value):
        self.filters.append(("eq", column, value))
        return self

    def ilike(self, column, value):
        self.filters.append(("ilike", column, value))
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def execute(self):
        return SimpleNamespace(data=[])


class FakeClient:
    def __init__(self):
        self.query = FakeQuery()

    def table(self, name):
        return self.query


def test_forecast_repository_matches_vessel_class_case_insensitively(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(
        "services.api.app.repositories.forecast_repository.get_supabase_client",
        lambda: client,
    )
    origin_id, destination_id = uuid4(), uuid4()

    ForecastRepository().list(
        origin_location_id=origin_id,
        destination_location_id=destination_id,
        vessel_class="Panamax",
    )

    assert ("eq", "origin_location_id", str(origin_id)) in client.query.filters
    assert ("eq", "destination_location_id", str(destination_id)) in client.query.filters
    assert ("ilike", "vessel_class", "Panamax") in client.query.filters
    assert ("eq", "vessel_class", "Panamax") not in client.query.filters


def test_market_repository_matches_vessel_class_case_insensitively(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(
        "services.api.app.repositories.market_repository.get_supabase_admin_client",
        lambda: client,
    )
    origin_id, destination_id = uuid4(), uuid4()

    MarketRepository().list(
        origin_location_id=origin_id,
        destination_location_id=destination_id,
        vessel_class="Panamax",
    )

    assert ("eq", "origin_location_id", str(origin_id)) in client.query.filters
    assert ("eq", "destination_location_id", str(destination_id)) in client.query.filters
    assert ("ilike", "vessel_class", "Panamax") in client.query.filters
    assert ("eq", "vessel_class", "Panamax") not in client.query.filters
