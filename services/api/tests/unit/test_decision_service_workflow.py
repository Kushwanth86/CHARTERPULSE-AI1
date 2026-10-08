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
        cargo_quantity_mt=70000,
        currency="USD",
        forecast_p10=20,
        forecast_p50=25,
        forecast_p90=30,
        now_expected_freight_cost=1750000,
        now_p90_freight_cost=2100000,
        wait_conservative_rate=30,
        wait_conservative_cost=2100000,
        wait_cost_difference=350000,
        wait_cost_difference_per_mt=5,
        probability_now_exceeds_baseline=0.5,
        risk_score=50,
        provenance="FORECAST",
        model_name="robust_recency_trend_baseline",
        forecast_id=forecast_id,
        rationale=[],
        warnings=[],
        generated_at="2026-10-08T00:00:00Z",
        route_snapshot={"status": "READY"},
        cost_snapshot={"status": "PARTIAL"},
        feasibility_snapshot={"status": "PENDING"},
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
        type("Payload", (), {"cargo_requirement_id": None})()
    )

    assert result.decision_run_id is not None
    assert fake.table_instance.inserted["forecast_snapshot"]["route_snapshot"] == {"status": "READY"}
    assert fake.table_instance.inserted["cost_snapshot"]["status"] == "PARTIAL"
    assert fake.table_instance.inserted["feasibility_snapshot"]["status"] == "PENDING"
