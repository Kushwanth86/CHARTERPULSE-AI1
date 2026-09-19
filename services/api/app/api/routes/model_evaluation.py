from fastapi import APIRouter, HTTPException, Query

from services.api.app.schemas.model_evaluation import (
    ForecastEvaluationCreate,
    ForecastEvaluationResponse,
    ModelEvaluationSummary,
)
from services.api.app.services.model_evaluation_service import (
    model_evaluation_service,
)


router = APIRouter(
    prefix="/api/v1/model-evaluations",
    tags=["model-evaluation"],
)


@router.post(
    "/forecast",
    response_model=ForecastEvaluationResponse,
)
def evaluate_forecast(
    payload: ForecastEvaluationCreate,
):
    try:
        return model_evaluation_service.evaluate_forecast(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get(
    "/forecast",
    response_model=list[ForecastEvaluationResponse],
)
def list_forecast_evaluations(
    model_name: str | None = None,
    model_version: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
):
    return model_evaluation_service.list(
        model_name=model_name,
        model_version=model_version,
        limit=limit,
    )


@router.get(
    "/forecast/summary",
    response_model=ModelEvaluationSummary,
)
def summarize_forecast_evaluations(
    model_name: str | None = None,
    model_version: str | None = None,
    limit: int = Query(default=500, ge=1, le=5000),
):
    try:
        return model_evaluation_service.summary(
            model_name=model_name,
            model_version=model_version,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
