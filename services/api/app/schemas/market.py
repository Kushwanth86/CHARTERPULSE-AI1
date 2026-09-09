from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class MarketObservationCreate(BaseModel):
    market_type: str = Field(min_length=1)
    metric: str = Field(min_length=1)

    origin_location_id: UUID | None = None
    destination_location_id: UUID | None = None

    vessel_class: str | None = None

    value: float = Field(gt=0)
    unit: str = Field(min_length=1)
    currency: str | None = None

    observed_at: datetime

    source: str = Field(min_length=1)
    source_reference: str | None = None

    provenance: str = Field(
        default="USER_PROVIDED",
        pattern="^(REAL|PUBLIC_PROXY|SIMULATED|USER_PROVIDED|DERIVED|FORECAST)$",
    )


class MarketObservationResponse(MarketObservationCreate):
    id: UUID
    created_at: datetime
