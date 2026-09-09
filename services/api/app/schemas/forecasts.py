from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class FreightForecastRequest(BaseModel):
    origin_location_id: UUID | None = None
    destination_location_id: UUID | None = None
    vessel_class: str | None = None

    forecast_horizon_days: int = Field(
        default=7,
        ge=0,
        le=365,
    )

    metric: str = "freight_rate"
    unit: str = "USD/MT"
    currency: str = "USD"


class FreightForecastResponse(BaseModel):
    id: UUID

    origin_location_id: UUID | None
    destination_location_id: UUID | None

    vessel_class: str | None

    forecast_horizon_days: int

    p10: float
    p50: float
    p90: float

    unit: str
    currency: str

    baseline_value: float

    model_name: str
    model_version: str

    mae: float | None
    rmse: float | None
    smape: float | None
    interval_coverage: float | None

    confidence: float

    provenance: str
    generated_at: datetime
    metadata: dict
