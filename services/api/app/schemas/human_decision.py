from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class HumanDecisionCreate(BaseModel):
    decision_run_id: str
    action: Literal["APPROVE", "MODIFY", "REJECT"]
    modified_parameters: dict[str, Any] = Field(default_factory=dict)
    reason: str | None = None
    actor_reference: str | None = None


class HumanDecisionResponse(BaseModel):
    id: str
    decision_run_id: str
    action: str
    modified_parameters: dict[str, Any]
    reason: str | None
    decided_at: datetime
    actor_reference: str | None
    provenance: str
