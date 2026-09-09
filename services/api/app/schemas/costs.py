from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


Provenance = Literal[
    "REAL",
    "PUBLIC_PROXY",
    "SIMULATED",
    "USER_PROVIDED",
    "DERIVED",
    "FORECAST",
]


class CostComponent(BaseModel):
    name: str
    amount: float = Field(ge=0)
    currency: str = "USD"
    unit: str = "TOTAL"
    provenance: Provenance
    source: str | None = None
    source_reference: str | None = None
    observed_at: datetime | None = None
    status: Literal["KNOWN", "ESTIMATED", "DERIVED", "MISSING"] = "KNOWN"


class TotalDeliveredCostRequest(BaseModel):
    cargo_requirement_id: UUID | None = None
    vessel_id: UUID | None = None
    forecast_id: UUID | None = None

    cargo_quantity_mt: float = Field(gt=0)

    ocean_freight_per_mt: float | None = Field(default=None, ge=0)
    bunker_cost: float | None = Field(default=None, ge=0)
    port_cost: float | None = Field(default=None, ge=0)
    canal_cost: float | None = Field(default=None, ge=0)
    loading_cost: float | None = Field(default=None, ge=0)
    discharge_cost: float | None = Field(default=None, ge=0)
    demurrage_cost: float | None = Field(default=None, ge=0)
    storage_cost: float | None = Field(default=None, ge=0)
    insurance_cost: float | None = Field(default=None, ge=0)
    delay_cost: float | None = Field(default=None, ge=0)
    inland_cost: float | None = Field(default=None, ge=0)
    risk_cost: float | None = Field(default=None, ge=0)

    currency: str = "USD"


class TotalDeliveredCostResponse(BaseModel):
    total_cost: float
    cost_per_mt: float
    currency: str

    completeness_score: float = Field(ge=0, le=1)

    components: list[CostComponent]

    known_component_count: int
    missing_component_count: int

    provenance: Literal["DERIVED", "SIMULATED", "USER_PROVIDED"]
    warnings: list[str] = Field(default_factory=list)
