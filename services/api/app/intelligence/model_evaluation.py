from __future__ import annotations

from math import sqrt
from statistics import mean


class ModelEvaluationEngine:
    """Calculate transparent forecast accuracy metrics from observed outcomes."""

    @staticmethod
    def evaluate(
        *,
        actual: float,
        p10: float,
        p50: float,
        p90: float,
    ) -> dict[str, float | bool]:
        if actual <= 0:
            raise ValueError("Actual value must be greater than zero.")
        if p10 < 0 or p50 < 0 or p90 < p50:
            raise ValueError("Forecast prediction interval is invalid.")

        signed_error = actual - p50
        absolute_error = abs(signed_error)
        squared_error = signed_error**2

        denominator = abs(actual) + abs(p50)
        smape = (
            200.0 * absolute_error / denominator
            if denominator > 0
            else 0.0
        )

        return {
            "signed_error": float(signed_error),
            "absolute_error": float(absolute_error),
            "squared_error": float(squared_error),
            "smape": float(smape),
            "interval_covered": bool(p10 <= actual <= p90),
        }

    @staticmethod
    def summarize(evaluations: list[dict]) -> dict:
        if not evaluations:
            raise ValueError("No forecast evaluations are available.")

        absolute_errors = [float(row["absolute_error"]) for row in evaluations]
        squared_errors = [float(row["squared_error"]) for row in evaluations]
        smapes = [float(row["smape"]) for row in evaluations]
        covered = [bool(row["interval_covered"]) for row in evaluations]

        return {
            "sample_count": len(evaluations),
            "mae": float(mean(absolute_errors)),
            "rmse": float(sqrt(mean(squared_errors))),
            "smape": float(mean(smapes)),
            "interval_coverage": float(mean(covered)),
        }
