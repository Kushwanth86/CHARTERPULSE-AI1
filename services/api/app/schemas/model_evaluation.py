from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


ActualProvenance = str


class ForecastEvaluationCreate(BaseModel):
    forecast_id: UUID
    actual_value: float = Field(gt=0)
    actual_observed_at: datetime
    actual_unit: str = Field(min_length=1, max_length=64)
    actual_currency: str | None = Field(default=None, min_length=3, max_length=16)
    actual_provenance: ActualProvenance = "USER_PROVIDED"
    source: str | None = None
    source_reference: str | None = None
    notes: str | None = None


class ForecastEvaluationResponse(ForecastEvaluationCreate):
    id: UUID
    evaluation_type: str
    model_name: str
    model_version: str
    predicted_p10: float
    predicted_p50: float
    predicted_p90: float
    signed_error: float
    absolute_error: float
    squared_error: float
    smape: float
    interval_covered: bool
    evaluated_at: datetime
    metadata: dict


class ModelEvaluationSummary(BaseModel):
    sample_count: int
    model_name: str | None = None
    model_version: str | None = None
    mae: float
    rmse: float
    smape: float
    interval_coverage: float
    evaluated_from: datetime | None = None
    evaluated_to: datetime | None = None
