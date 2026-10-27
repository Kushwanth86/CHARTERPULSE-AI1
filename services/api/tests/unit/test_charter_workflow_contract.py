
from datetime import datetime, timezone
from uuid import uuid4

from services.api.app.decision.decision_engine import (
    DecisionResponse,
)


def test_decision_response_exposes_charter_workflow_snapshots():
    """The decision contract carries workflow evidence for the UI."""
    response = DecisionResponse(
        decision_status="PRELIMINARY",
        recommendation="CHARTER_NOW",
        cargo_quantity_mt=70000,
        currency="USD",
        forecast_p10=20.0,
        forecast_p50=25.0,
        forecast_p90=30.0,
        now_expected_freight_cost=1_750_000,
        now_p90_freight_cost=2_100_000,
        wait_conservative_rate=30.0,
        wait_conservative_cost=2_100_000,
        wait_cost_difference=350_000,
        wait_cost_difference_per_mt=5.0,
        probability_now_exceeds_baseline=0.5,
        risk_score=50.0,
        provenance="FORECAST",
        model_name="robust_recency_trend_baseline",
        forecast_id=uuid4(),
        rationale=[],
        warnings=[],
        generated_at="2026-10-08T00:00:00Z",
        route_snapshot={"status": "IDENTIFIED"},
        cost_snapshot={"status": "PARTIAL"},
        feasibility_snapshot={"status": "PENDING"},
    )

    assert response.route_snapshot["status"] == "IDENTIFIED"
    assert response.cost_snapshot["status"] == "PARTIAL"
    assert response.feasibility_snapshot["status"] == "PENDING"


def test_evaluate_decision_builds_route_and_cost_snapshots(monkeypatch):
    class Risk:
        expected_cost = 1_750_000.0
        p90_cost = 2_100_000.0
        probability_cost_above_baseline = 0.5
        risk_score = 50.0

    forecast_id = uuid4()

    monkeypatch.setattr(
        "services.api.app.decision.decision_engine._get_forecast",
        lambda value: {
            "id": str(forecast_id),
            "p10": 20.0,
            "p50": 25.0,
            "p90": 30.0,
            "unit": "USD/MT",
            "origin_location_id": "origin-1",
            "destination_location_id": "destination-1",
            "vessel_class": "PANAMAX",
            "provenance": "FORECAST",
            "model_name": "robust_recency_trend_baseline",
            "generated_at": "2026-10-26T10:00:00+00:00",
            "metadata": {
                "route_scoped": True,
                "input_provenance": "MARKET_OBSERVATION",
                "observation_count": 12,
                "distinct_observation_dates": 12,
                "source_provenances": ["REAL"],
                "source_labels": ["Verified test provider"],
                "latest_observation_at": datetime.now(timezone.utc).isoformat(),
            },
        },
    )

    cargo_id = uuid4()
    monkeypatch.setattr(
        "services.api.app.decision.decision_engine._get_cargo_requirement",
        lambda value: {
            "id": str(cargo_id),
            "quantity_mt": "70000",
            "origin_location_id": "origin-1",
            "destination_location_id": "destination-1",
            "vessel_class": "PANAMAX",
        },
    )

    monkeypatch.setattr(
        "services.api.app.decision.decision_engine.simulate_freight_risk",
        lambda **kwargs: Risk(),
    )

    from services.api.app.decision.decision_engine import (
        DecisionRequest,
        evaluate_decision,
    )

    response = evaluate_decision(
        DecisionRequest(
            forecast_id=forecast_id,
            cargo_requirement_id=cargo_id,
            cargo_quantity_mt=70_000,
        )
    )

    # The test forecast has explicit source and route evidence.
    assert response.route_snapshot == {
        "status": "IDENTIFIED",
        "validation_status": "SOURCE_MATCHED",
        "origin_location_id": "origin-1",
        "destination_location_id": "destination-1",
        "vessel_class": "PANAMAX",
    }

    assert response.cost_snapshot["status"] == "PARTIAL"
    assert response.cost_snapshot["known_components"] == [
        "ocean_freight"
    ]
    assert "bunker" in response.cost_snapshot["missing_components"]
    assert "insurance" in response.cost_snapshot["missing_components"]
    assert (
        response.cost_snapshot["now_expected_freight_cost"]
        == 1_750_000.0
    )
    assert response.feasibility_snapshot["status"] == "PENDING"
    assert response.decision_status == "PRELIMINARY"
