import pytest
from uuid import uuid4

from services.api.app.decision import decision_engine


@pytest.mark.parametrize(
    "input_provenance",
    ["SIMULATED", "SIMULATED_REFERENCE", "SYNTHETIC"],
)
def test_decision_rejects_simulated_forecast_inputs(monkeypatch, input_provenance):
    forecast_id = uuid4()
    monkeypatch.setattr(
        decision_engine,
        "_get_forecast",
        lambda _forecast_id: {
            "id": str(forecast_id),
            "p10": 20.0,
            "p50": 25.0,
            "p90": 30.0,
            # The record label must not override its input data provenance.
            "provenance": "FORECAST",
            "metadata": {"input_provenance": input_provenance},
        },
    )

    request = decision_engine.DecisionRequest(
        forecast_id=forecast_id,
        cargo_quantity_mt=1000,
    )

    with pytest.raises(
        ValueError,
        match=f"verified market observations.*{input_provenance}",
    ):
        decision_engine.evaluate_decision(request)


def test_decision_uses_verified_input_provenance(monkeypatch):
    forecast_id = uuid4()
    monkeypatch.setattr(
        decision_engine,
        "_get_forecast",
        lambda _forecast_id: {
            "id": str(forecast_id),
            "p10": 20.0,
            "p50": 25.0,
            "p90": 30.0,
            "provenance": "FORECAST",
            "metadata": {"input_provenance": "MARKET_OBSERVATION"},
            "model_name": "test-model",
        },
    )

    request = decision_engine.DecisionRequest(
        forecast_id=forecast_id,
        cargo_quantity_mt=1000,
        simulations=100,
    )

    result = decision_engine.evaluate_decision(request)

    assert result.provenance == "MARKET_OBSERVATION"
