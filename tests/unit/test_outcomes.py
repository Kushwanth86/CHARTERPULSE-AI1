from datetime import datetime, timezone
from uuid import UUID, uuid4

from services.api.app.schemas.outcomes import (
    DecisionFeedbackCreate,
    DecisionOutcomeCreate,
)
from services.api.app.services.outcome_service import (
    FeedbackService,
    OutcomeService,
)


USER_ID = UUID("00000000-0000-4000-8000-000000000123")


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeTable:
    def __init__(self, row):
        self.row = row
        self.payload = None
        self.filters = []
        self.selection = False

    def select(self, fields):
        self.selection = True
        return self

    def eq(self, column, value):
        self.filters.append((column, value))
        return self

    def limit(self, value):
        return self

    def insert(self, payload):
        self.payload = payload
        return self

    def execute(self):
        if self.selection:
            row_id = str(self.row.get("id", ""))
            if self.filters and any(column == "id" and value != row_id for column, value in self.filters):
                return FakeResponse([])
            return FakeResponse([self.row])
        return FakeResponse([self.row | (self.payload or {})])


class FakeClient:
    def __init__(self, rows):
        self.tables = {
            name: FakeTable(row)
            for name, row in rows.items()
        }
        self.tables.setdefault("decision_runs", FakeTable({"id": str(USER_ID), "user_id": str(USER_ID)}))
        self.tables.setdefault("human_decisions", FakeTable({"id": str(USER_ID), "user_id": str(USER_ID)}))
        self.tables.setdefault("decision_outcomes", FakeTable({"id": str(USER_ID), "user_id": str(USER_ID)}))

    def table(self, name):
        return self.tables[name]


def test_outcome_service_persists_actual_outcome(monkeypatch):
    decision_run_id = uuid4()
    outcome_id = uuid4()
    recorded_at = datetime.now(timezone.utc)

    client = FakeClient(
        {
            "decision_runs": {"id": str(decision_run_id), "user_id": str(USER_ID)},
            "decision_outcomes": {
                "id": outcome_id,
                "recorded_at": recorded_at,
            },
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

    result = OutcomeService().create_outcome(payload, USER_ID)

    assert result.id == outcome_id
    assert result.decision_run_id == decision_run_id
    assert result.actual_freight_rate_per_mt == 28.5
    assert result.actual_total_cost == 199500
    assert result.provenance == "USER_PROVIDED"
    assert client.tables["decision_outcomes"].payload["source"] == "TEST_SOURCE"


def test_feedback_service_persists_human_feedback(monkeypatch):
    decision_run_id = uuid4()
    outcome_id = uuid4()
    feedback_id = uuid4()
    created_at = datetime.now(timezone.utc)

    client = FakeClient(
        {
            "decision_runs": {"id": str(decision_run_id), "user_id": str(USER_ID)},
            "decision_outcomes": {"id": outcome_id, "user_id": str(USER_ID)},
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

    result = FeedbackService().create_feedback(payload, USER_ID)

    assert result.id == feedback_id
    assert result.decision_run_id == decision_run_id
    assert result.outcome_id == outcome_id
    assert result.rating == 4
    assert result.recommendation_followed is True
    assert result.correctness == "PARTIALLY_CORRECT"
