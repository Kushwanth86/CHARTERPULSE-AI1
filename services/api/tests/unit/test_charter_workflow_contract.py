import pytest

from services.api.app.decision.decision_engine import DecisionResponse


def test_decision_response_exposes_charter_workflow_snapshots():
    """The decision contract must carry the workflow evidence needed by the UI."""
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
        forecast_id="6e7e8284-9b73-49b1-9767-30f536a7911a",
        rationale=[],
        warnings=[],
        generated_at="2026-10-08T00:00:00Z",
        route_snapshot={"status": "READY"},
        cost_snapshot={"status": "PARTIAL"},
        feasibility_snapshot={"status": "PENDING"},
    )

    assert response.route_snapshot["status"] == "READY"
    assert response.cost_snapshot["status"] == "PARTIAL"
    assert response.feasibility_snapshot["status"] == "PENDING"
