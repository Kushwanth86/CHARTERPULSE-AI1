from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


OutcomeProvenance = Literal["REAL", "USER_PROVIDED", "DERIVED"]


class DecisionOutcomeCreate(BaseModel):
    decision_run_id: UUID
    human_decision_id: UUID | None = None

    actual_freight_rate_per_mt: float | None = Field(default=None, ge=0)
    actual_total_cost: float | None = Field(default=None, ge=0)
    currency: str = "USD"

    actual_cost_components: dict[str, Any] = Field(default_factory=dict)

    actual_delivery_at: datetime | None = None
    delivery_delay_days: float | None = Field(default=None, ge=0)

    source: str | None = None
    source_reference: str | None = None
    provenance: OutcomeProvenance = "USER_PROVIDED"
    notes: str | None = None


class DecisionOutcomeResponse(DecisionOutcomeCreate):
    id: UUID
    recorded_at: datetime


Correctness = Literal[
    "CORRECT",
    "PARTIALLY_CORRECT",
    "INCORRECT",
    "NOT_EVALUATED",
]


class DecisionFeedbackCreate(BaseModel):
    decision_run_id: UUID
    outcome_id: UUID | None = None

    rating: int | None = Field(default=None, ge=1, le=5)
    recommendation_followed: bool | None = None
    correctness: Correctness = "NOT_EVALUATED"

    comment: str | None = None
    actor_reference: str | None = None
    provenance: Literal["USER_PROVIDED", "DERIVED"] = "USER_PROVIDED"


class DecisionFeedbackResponse(DecisionFeedbackCreate):
    id: UUID
    created_at: datetime
