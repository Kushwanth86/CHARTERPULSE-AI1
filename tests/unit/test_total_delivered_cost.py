from uuid import uuid4

import pytest

from services.api.app.intelligence import total_delivered_cost as cost_module
from services.api.app.schemas.costs import TotalDeliveredCostRequest


def test_total_delivered_cost_multiplies_ocean_freight_by_cargo_quantity():
    payload = TotalDeliveredCostRequest(
        cargo_quantity_mt=70_000,
        ocean_freight_per_mt=25,
        bunker_cost=100_000,
        port_cost=50_000,
        currency="USD",
    )

    result = cost_module.calculate_total_delivered_cost(payload)

    assert result.total_cost == 1_900_000
    assert result.cost_per_mt == pytest.approx(27.1429, abs=0.0001)
    assert result.known_component_count == 3
    assert result.missing_component_count == 9
    assert result.completeness_score == pytest.approx(0.25)
    assert result.provenance == "USER_PROVIDED"


def test_total_delivered_cost_warns_when_components_are_missing():
    payload = TotalDeliveredCostRequest(
        cargo_quantity_mt=10_000,
        ocean_freight_per_mt=20,
    )

    result = cost_module.calculate_total_delivered_cost(payload)

    assert result.total_cost == 200_000
    assert result.known_component_count == 1
    assert result.missing_component_count == 11
    assert result.completeness_score == pytest.approx(1 / 12)
    assert result.warnings
    assert "partial delivered-cost estimate" in result.warnings[0]


def test_total_delivered_cost_can_use_forecast_p50(monkeypatch):
    forecast_id = uuid4()

    monkeypatch.setattr(
        cost_module,
        "_get_forecast",
        lambda value: {
            "id": str(value),
            "p50": 30.0,
            "model_name": "statistical_baseline",
            "generated_at": "2026-09-14T05:00:00Z",
        },
    )

    payload = TotalDeliveredCostRequest(
        cargo_quantity_mt=20_000,
        forecast_id=forecast_id,
        port_cost=100_000,
        currency="USD",
    )

    result = cost_module.calculate_total_delivered_cost(payload)

    assert result.total_cost == 700_000
    assert result.cost_per_mt == 35
    assert result.provenance == "DERIVED"

    ocean = next(item for item in result.components if item.name == "Ocean Freight")
    assert ocean.amount == 600_000
    assert ocean.provenance == "FORECAST"
    assert ocean.status == "DERIVED"
    assert ocean.source == "statistical_baseline"


def test_total_delivered_cost_rejects_missing_forecast(monkeypatch):
    forecast_id = uuid4()
    monkeypatch.setattr(cost_module, "_get_forecast", lambda value: None)

    payload = TotalDeliveredCostRequest(
        cargo_quantity_mt=20_000,
        forecast_id=forecast_id,
    )

    with pytest.raises(ValueError, match="was not found"):
        cost_module.calculate_total_delivered_cost(payload)


def test_total_delivered_cost_rejects_forecast_without_p50(monkeypatch):
    forecast_id = uuid4()
    monkeypatch.setattr(cost_module, "_get_forecast", lambda value: {"id": str(value)})

    payload = TotalDeliveredCostRequest(
        cargo_quantity_mt=20_000,
        forecast_id=forecast_id,
    )

    with pytest.raises(ValueError, match="has no P50"):
        cost_module.calculate_total_delivered_cost(payload)
