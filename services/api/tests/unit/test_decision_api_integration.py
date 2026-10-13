from uuid import uuid4

from fastapi.testclient import TestClient

from services.api.app.api.routes import decision as decision_route
from services.api.app.decision.decision_engine import DecisionResponse
from services.api.app.main import app


client = TestClient(app)


def test_evaluate_decision_returns_workflow_snapshots(monkeypatch):
    forecast_id = uuid4()
    run_id = str(uuid4())

    decision = DecisionResponse(
        decision_run_id=run_id,
        decision_status="PRELIMINARY",
        recommendation="CHARTER_NOW",
        cargo_quantity_mt=70000.0,
        currency="USD",
        forecast_p10=20.0,
        forecast_p50=25.0,
        forecast_p90=30.0,
        now_expected_freight_cost=1750000.0,
        now_p90_freight_cost=2100000.0,
        wait_conservative_rate=30.0,
        wait_conservative_cost=2100000.0,
        wait_cost_difference=350000.0,
        wait_cost_difference_per_mt=5.0,
        probability_now_exceeds_baseline=0.5,
        risk_score=50.0,
        provenance="FORECAST",
        model_name="test-model",
        forecast_id=forecast_id,
        rationale=[],
        warnings=["PRELIMINARY decision"],
        generated_at="2026-10-08T00:00:00Z",
        route_snapshot={
            "status": "IDENTIFIED",
            "validation_status": "NOT_VALIDATED",
        },
        cost_snapshot={
            "status": "PARTIAL",
            "known_components": ["ocean_freight"],
            "missing_components": ["bunker", "insurance"],
        },
        feasibility_snapshot={"status": "PENDING"},
    )

    monkeypatch.setattr(
        decision_route.service,
        "evaluate",
        lambda payload: decision,
    )

    response = client.post(
        "/api/v1/decision/evaluate",
        json={
            "forecast_id": str(forecast_id),
            "cargo_quantity_mt": 70000,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["decision_run_id"] == run_id
    assert body["decision_status"] == "PRELIMINARY"
    assert body["route_snapshot"]["validation_status"] == "NOT_VALIDATED"
    assert body["cost_snapshot"]["status"] == "PARTIAL"
    assert body["feasibility_snapshot"]["status"] == "PENDING"


def test_evaluate_decision_rejects_invalid_request():
    response = client.post(
        "/api/v1/decision/evaluate",
        json={
            "forecast_id": "not-a-uuid",
            "cargo_quantity_mt": -10,
        },
    )

    assert response.status_code == 422
