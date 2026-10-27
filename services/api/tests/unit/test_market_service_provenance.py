from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest
from pydantic import ValidationError

from services.api.app.schemas.market import MarketObservationCreate
from services.api.app.services.market_service import MarketService


USER_ID = UUID("00000000-0000-4000-8000-000000000123")


def observation_payload(provenance: str = "REAL", value: float = 20.0) -> MarketObservationCreate:
    return MarketObservationCreate(
        market_type="FREIGHT",
        metric="OCEAN_FREIGHT",
        value=value,
        unit="USD/MT",
        currency="USD",
        observed_at=datetime(2026, 10, 20, tzinfo=timezone.utc),
        source="User-supplied label",
        source_reference="https://example.invalid/not-attested",
        provenance=provenance,
    )


@pytest.mark.parametrize(
    "claimed_provenance",
    ["REAL", "PUBLIC_PROXY", "SIMULATED", "DERIVED", "FORECAST"],
)
def test_public_market_write_cannot_self_assert_provenance(
    monkeypatch, claimed_provenance
):
    class RecordingRepository:
        payload = None

        def create(self, payload, user_id):
            self.payload = payload
            return payload

    repository = RecordingRepository()
    monkeypatch.setattr(
        "services.api.app.services.market_service.MarketRepository",
        lambda: repository,
    )

    result = MarketService().create(observation_payload(claimed_provenance), USER_ID)

    assert repository.payload["provenance"] == "USER_PROVIDED"
    assert result["provenance"] == "USER_PROVIDED"


@pytest.mark.parametrize("value", [float("inf"), float("-inf"), float("nan")])
def test_market_observation_rejects_non_finite_values(value):
    with pytest.raises(ValidationError):
        observation_payload(value=value)


@pytest.mark.parametrize("value", [0, -1, -0.001])
def test_market_observation_rejects_non_positive_values(value):
    with pytest.raises(ValidationError):
        observation_payload(value=value)
