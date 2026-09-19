from __future__ import annotations

from services.api.app.intelligence.model_evaluation import ModelEvaluationEngine
from services.api.app.repositories.model_evaluation_repository import (
    ModelEvaluationRepository,
)
from services.api.app.schemas.model_evaluation import (
    ForecastEvaluationCreate,
    ForecastEvaluationResponse,
    ModelEvaluationSummary,
)


class ModelEvaluationService:
    def __init__(self) -> None:
        self.repository = ModelEvaluationRepository()
        self.engine = ModelEvaluationEngine()

    def evaluate_forecast(
        self,
        payload: ForecastEvaluationCreate,
    ) -> ForecastEvaluationResponse:
        forecast = self.repository.get_forecast(payload.forecast_id)

        if not forecast:
            raise ValueError("Forecast was not found.")

        metrics = self.engine.evaluate(
            actual=payload.actual_value,
            p10=float(forecast["p10"]),
            p50=float(forecast["p50"]),
            p90=float(forecast["p90"]),
        )

        row = {
            "forecast_id": str(payload.forecast_id),
            "evaluation_type": "FORECAST_ACCURACY",
            "model_name": forecast["model_name"],
            "model_version": forecast["model_version"],
            "actual_value": payload.actual_value,
            "actual_unit": payload.actual_unit,
            "actual_currency": payload.actual_currency,
            "actual_observed_at": payload.actual_observed_at.isoformat(),
            "predicted_p10": forecast["p10"],
            "predicted_p50": forecast["p50"],
            "predicted_p90": forecast["p90"],
            **metrics,
            "actual_provenance": payload.actual_provenance,
            "source": payload.source,
            "source_reference": payload.source_reference,
            "notes": payload.notes,
            "metadata": {
                "forecast_generated_at": forecast.get("generated_at"),
                "forecast_horizon_days": forecast.get("forecast_horizon_days"),
                "forecast_unit": forecast.get("unit"),
                "forecast_currency": forecast.get("currency"),
            },
        }

        return ForecastEvaluationResponse.model_validate(
            self.repository.create(row)
        )

    def list(
        self,
        *,
        model_name: str | None = None,
        model_version: str | None = None,
        limit: int = 100,
    ) -> list[ForecastEvaluationResponse]:
        rows = self.repository.list(
            model_name=model_name,
            model_version=model_version,
            limit=limit,
        )
        return [ForecastEvaluationResponse.model_validate(row) for row in rows]

    def summary(
        self,
        *,
        model_name: str | None = None,
        model_version: str | None = None,
        limit: int = 500,
    ) -> ModelEvaluationSummary:
        rows = self.repository.list(
            model_name=model_name,
            model_version=model_version,
            limit=limit,
        )

        if not rows:
            raise ValueError("No forecast evaluations are available.")

        summary = self.engine.summarize(rows)
        summary["model_name"] = model_name or rows[0].get("model_name")
        summary["model_version"] = model_version or rows[0].get("model_version")

        evaluated_times = [row.get("evaluated_at") for row in rows if row.get("evaluated_at")]
        if evaluated_times:
            summary["evaluated_from"] = min(evaluated_times)
            summary["evaluated_to"] = max(evaluated_times)

        return ModelEvaluationSummary.model_validate(summary)


model_evaluation_service = ModelEvaluationService()
