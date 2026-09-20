from datetime import datetime, timezone
from uuid import uuid4

from services.api.app.schemas.outcomes import (
    DecisionFeedbackCreate,
    DecisionOutcomeCreate,
)
from services.api.app.services.outcome_service import (
    FeedbackService,
    OutcomeService,
)


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeTable:
    def __init__(self, row):
        self.row = row
        self.payload = None

    def insert(self, payload):
        self.payload = payload
        return self

    def execute(self):
        return FakeResponse([self.row | self.payload])


class FakeClient:
    def __init__(self, rows):
        self.tables = {
            name: FakeTable(row)
            for name, row in rows.items()
        }

    def table(self, name):
        return self.tables[name]


def test_outcome_service_persists_actual_outcome(monkeypatch):
    decision_run_id = uuid4()
    outcome_id = uuid4()
    recorded_at = datetime.now(timezone.utc)

    client = FakeClient(
        {
            "decision_outcomes": {
                "id": outcome_id,
                "recorded_at": recorded_at,
            }
        }
    )
    monkeypatch.setattr(
        "services.api.app.services.outcome_service.get_supabase_admin_client",
        lambda: client,
    )

    payload = DecisionOutcomeCreate(
        decision_run_id=decision_run_id,
        actual_freight_rate_per_mt=28.5,
        actual_total_cost=199500,
        currency="USD",
        actual_cost_components={"ocean_freight": 199500},
        provenance="REAL",
        source="TEST_SOURCE",
    )

    result = OutcomeService().create_outcome(payload)

    assert result.id == outcome_id
    assert result.decision_run_id == decision_run_id
    assert result.actual_freight_rate_per_mt == 28.5
    assert result.actual_total_cost == 199500
    assert result.provenance == "REAL"
    assert client.tables["decision_outcomes"].payload["source"] == "TEST_SOURCE"


def test_feedback_service_persists_human_feedback(monkeypatch):
    decision_run_id = uuid4()
    outcome_id = uuid4()
    feedback_id = uuid4()
    created_at = datetime.now(timezone.utc)

    client = FakeClient(
        {
            "decision_feedback": {
                "id": feedback_id,
                "created_at": created_at,
            }
        }
    )
    monkeypatch.setattr(
        "services.api.app.services.outcome_service.get_supabase_admin_client",
        lambda: client,
    )

    payload = DecisionFeedbackCreate(
        decision_run_id=decision_run_id,
        outcome_id=outcome_id,
        rating=4,
        recommendation_followed=True,
        correctness="PARTIALLY_CORRECT",
        comment="Useful recommendation; port delay was underestimated.",
        actor_reference="TEST_ACTOR",
    )

    result = FeedbackService().create_feedback(payload)

    assert result.id == feedback_id
    assert result.decision_run_id == decision_run_id
    assert result.outcome_id == outcome_id
    assert result.rating == 4
    assert result.recommendation_followed is True
    assert result.correctness == "PARTIALLY_CORRECT"
