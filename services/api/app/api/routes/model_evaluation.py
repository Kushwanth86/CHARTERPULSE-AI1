from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from services.api.app.schemas.model_evaluation import (
    ForecastEvaluationCreate,
    ForecastEvaluationResponse,
    ModelEvaluationSummary,
)
from services.api.app.security.current_user import get_current_user_id
from services.api.app.services.model_evaluation_service import (
    model_evaluation_service,
)


router = APIRouter(
    prefix="/api/v1/model-evaluations",
    tags=["model-evaluation"],
)


@router.post("/forecast", response_model=ForecastEvaluationResponse)
def evaluate_forecast(
    payload: ForecastEvaluationCreate,
    user_id: UUID = Depends(get_current_user_id),
):
    try:
        return model_evaluation_service.evaluate_forecast(payload, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/forecast", response_model=list[ForecastEvaluationResponse])
def list_forecast_evaluations(
    model_name: str | None = None,
    model_version: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    user_id: UUID = Depends(get_current_user_id),
):
    return model_evaluation_service.list(
        user_id=user_id,
        model_name=model_name,
        model_version=model_version,
        limit=limit,
    )


@router.get("/forecast/summary", response_model=ModelEvaluationSummary)
def summarize_forecast_evaluations(
    model_name: str | None = None,
    model_version: str | None = None,
    limit: int = Query(default=500, ge=1, le=5000),
    user_id: UUID = Depends(get_current_user_id),
):
    try:
        return model_evaluation_service.summary(
            user_id=user_id,
            model_name=model_name,
            model_version=model_version,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
