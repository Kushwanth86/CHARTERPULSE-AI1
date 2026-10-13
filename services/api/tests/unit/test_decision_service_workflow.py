
from uuid import uuid4

from services.api.app.decision.decision_engine import DecisionResponse
from services.api.app.services.decision_service import DecisionService


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeTable:
    def __init__(self, rows):
        self.rows = rows
        self.inserted = None

    def insert(self, row):
        self.inserted = row
        return self

    def execute(self):
        return FakeResponse(self.rows)


class FakeSupabase:
    def __init__(self):
        self.table_instance = FakeTable([{"id": str(uuid4())}])

    def table(self, name):
        assert name == "decision_runs"
        return self.table_instance


def test_decision_service_persists_all_workflow_snapshots(monkeypatch):
    forecast_id = uuid4()

    decision = DecisionResponse(
        decision_status="PRELIMINARY",
        recommendation="CHARTER_NOW",
        cargo_quantity_mt=70_000,
        currency="USD",
        forecast_p10=20.0,
        forecast_p50=25.0,
        forecast_p90=30.0,
        now_expected_freight_cost=1_750_000.0,
        now_p90_freight_cost=2_100_000.0,
        wait_conservative_rate=30.0,
        wait_conservative_cost=2_100_000.0,
        wait_cost_difference=350_000.0,
        wait_cost_difference_per_mt=5.0,
        probability_now_exceeds_baseline=0.5,
        risk_score=50.0,
        provenance="FORECAST",
        model_name="robust_recency_trend_baseline",
        forecast_id=forecast_id,
        rationale=[],
        warnings=[],
        generated_at="2026-10-08T00:00:00Z",
        route_snapshot={
            "status": "IDENTIFIED",
            "validation_status": "NOT_VALIDATED",
        },
        cost_snapshot={
            "status": "PARTIAL",
            "known_components": ["ocean_freight"],
            "missing_components": ["bunker", "insurance"],
            "now_expected_freight_cost": 1_750_000.0,
        },
        feasibility_snapshot={
            "status": "PENDING",
            "reason": "Vessel and port constraints have not been validated.",
        },
    )

    fake = FakeSupabase()

    monkeypatch.setattr(
        "services.api.app.services.decision_service.evaluate_decision",
        lambda payload: decision,
    )
    monkeypatch.setattr(
        "services.api.app.services.decision_service.get_supabase_admin_client",
        lambda: fake,
    )

    result = DecisionService().evaluate(
        type(
            "Payload",
            (),
            {"cargo_requirement_id": None},
        )()
    )

    row = fake.table_instance.inserted

    assert result.decision_run_id is not None

    # Route information is persisted inside the forecast snapshot.
    assert row["forecast_snapshot"]["route_snapshot"] == {
        "status": "IDENTIFIED",
        "validation_status": "NOT_VALIDATED",
    }

    # Cost evidence must preserve its completeness status.
    assert row["cost_snapshot"]["status"] == "PARTIAL"
    assert row["cost_snapshot"]["now_expected_freight_cost"] == (
        1_750_000.0
    )
    assert row["cost_snapshot"]["known_components"] == [
        "ocean_freight"
    ]
    assert "bunker" in row["cost_snapshot"]["missing_components"]

    # Never store a freight-only estimate as total delivered cost.
    assert row["expected_total_cost"] is None

    assert row["feasibility_snapshot"]["status"] == "PENDING"

    assert row["risk_snapshot"]["risk_score"] == 50.0
    assert (
        row["risk_snapshot"]["probability_now_exceeds_baseline"]
        == 0.5
    )



def test_decision_service_raises_when_persistence_returns_no_rows(monkeypatch):
    from types import SimpleNamespace

    import pytest

    decision = DecisionResponse(
        decision_status="PRELIMINARY",
        recommendation="CHARTER_NOW",
        cargo_quantity_mt=70_000,
        currency="USD",
        forecast_p10=20.0,
        forecast_p50=25.0,
        forecast_p90=30.0,
        now_expected_freight_cost=1_750_000.0,
        now_p90_freight_cost=2_100_000.0,
        wait_conservative_rate=30.0,
        wait_conservative_cost=2_100_000.0,
        wait_cost_difference=350_000.0,
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

    fake = FakeSupabase()
    fake.table_instance.rows = []

    monkeypatch.setattr(
        "services.api.app.services.decision_service.evaluate_decision",
        lambda payload: decision,
    )
    monkeypatch.setattr(
        "services.api.app.services.decision_service.get_supabase_admin_client",
        lambda: fake,
    )

    with pytest.raises(
        RuntimeError,
        match="Decision could not be persisted to decision_runs",
    ):
        DecisionService().evaluate(
            SimpleNamespace(cargo_requirement_id=None)
        )
