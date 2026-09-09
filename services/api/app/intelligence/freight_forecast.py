from __future__ import annotations

from datetime import datetime, timezone
from math import sqrt
from statistics import median
from typing import Any

import numpy as np


class FreightForecastEngine:
    """
    Transparent statistical baseline.

    The engine never creates a market price when there are no
    observations.

    Strategy:
      - sort observations chronologically
      - use recency-weighted values
      - estimate linear trend when enough observations exist
      - calculate residual uncertainty
      - produce P10/P50/P90
      - calculate simple holdout metrics where possible
    """

    model_name = "robust_recency_trend_baseline"
    model_version = "1.0.0"

    def _values(self, observations: list[dict]) -> np.ndarray:
        values = []

        for row in observations:
            try:
                value = float(row["value"])
            except (KeyError, TypeError, ValueError):
                continue

            if np.isfinite(value) and value > 0:
                values.append(value)

        return np.asarray(values, dtype=float)

    def _recency_weights(self, count: int) -> np.ndarray:
        if count <= 0:
            return np.asarray([], dtype=float)

        positions = np.arange(count, dtype=float)

        # Recent observations receive more weight.
        weights = np.exp(
            (positions - (count - 1)) / max(3.0, count / 3.0)
        )

        return weights / weights.sum()

    def _weighted_baseline(self, values: np.ndarray) -> float:
        weights = self._recency_weights(len(values))

        return float(np.sum(values * weights))

    def _trend_forecast(
        self,
        observations: list[dict],
        horizon_days: int,
    ) -> tuple[float, float]:

        usable = []

        for row in observations:
            try:
                timestamp = datetime.fromisoformat(
                    str(row["observed_at"]).replace("Z", "+00:00")
                )
                value = float(row["value"])

                if np.isfinite(value) and value > 0:
                    usable.append((timestamp, value))

            except (KeyError, TypeError, ValueError):
                continue

        if len(usable) < 3:
            values = np.asarray(
                [value for _, value in usable],
                dtype=float,
            )

            return (
                self._weighted_baseline(values),
                0.0,
            )

        usable.sort(key=lambda item: item[0])

        start = usable[0][0]

        x = np.asarray(
            [
                (timestamp - start).total_seconds() / 86400.0
                for timestamp, _ in usable
            ],
            dtype=float,
        )

        y = np.asarray(
            [value for _, value in usable],
            dtype=float,
        )

        weights = self._recency_weights(len(y))

        try:
            slope, intercept = np.polyfit(
                x,
                y,
                1,
                w=np.sqrt(weights),
            )

            future_x = x[-1] + max(0, horizon_days)

            prediction = float(
                intercept + slope * future_x
            )

            prediction = max(
                prediction,
                float(np.min(y)) * 0.25,
            )

            fitted = intercept + slope * x

            residuals = y - fitted

            residual_scale = float(
                np.std(residuals, ddof=1)
                if len(residuals) > 1
                else 0.0
            )

            return prediction, residual_scale

        except (ValueError, np.linalg.LinAlgError):
            return self._weighted_baseline(y), 0.0

    def _backtest(
        self,
        observations: list[dict],
    ) -> tuple[float | None, float | None, float | None]:

        values = self._values(observations)

        if len(values) < 5:
            return None, None, None

        split = max(
            3,
            int(len(values) * 0.8),
        )

        train = values[:split]
        actual = values[split:]

        if len(actual) == 0:
            return None, None, None

        prediction = self._weighted_baseline(train)

        errors = actual - prediction

        mae = float(np.mean(np.abs(errors)))
        rmse = float(
            sqrt(np.mean(np.square(errors)))
        )

        denominator = np.abs(actual) + np.abs(prediction)

        valid = denominator > 0

        if np.any(valid):
            smape = float(
                np.mean(
                    2.0
                    * np.abs(errors[valid])
                    / denominator[valid]
                )
                * 100.0
            )
        else:
            smape = None

        return mae, rmse, smape

    def forecast(
        self,
        observations: list[dict],
        horizon_days: int,
    ) -> dict[str, Any]:

        values = self._values(observations)

        if len(values) == 0:
            raise ValueError(
                "No usable freight observations are available. "
                "A forecast cannot be generated without observations."
            )

        baseline, residual_scale = self._trend_forecast(
            observations,
            horizon_days,
        )

        # Empirical dispersion is used when trend residuals are
        # unavailable or too small.
        empirical_std = float(
            np.std(values, ddof=1)
            if len(values) > 1
            else 0.0
        )

        uncertainty = max(
            residual_scale,
            empirical_std,
            abs(baseline) * 0.05,
        )

        p50 = max(
            baseline,
            float(np.min(values)) * 0.25,
        )

        p10 = max(
            p50 - 1.2816 * uncertainty,
            0.0,
        )

        p90 = p50 + 1.2816 * uncertainty

        mae, rmse, smape = self._backtest(
            observations
        )

        sample_score = min(
            1.0,
            len(values) / 30.0,
        )

        dispersion_ratio = (
            uncertainty / p50
            if p50 > 0
            else 1.0
        )

        stability_score = max(
            0.0,
            min(
                1.0,
                1.0 - dispersion_ratio,
            ),
        )

        confidence = (
            0.55 * sample_score
            + 0.45 * stability_score
        )

        confidence = float(
            max(
                0.0,
                min(1.0, confidence),
            )
        )

        now = datetime.now(timezone.utc)

        return {
            "p10": float(p10),
            "p50": float(p50),
            "p90": float(p90),
            "baseline_value": float(p50),

            "model_name": self.model_name,
            "model_version": self.model_version,

            "mae": mae,
            "rmse": rmse,
            "smape": smape,

            "interval_coverage": None,

            "confidence": confidence,

            "provenance": "FORECAST",

            "generated_at": now.isoformat(),

            "metadata": {
                "observation_count": int(len(values)),
                "minimum_observation": float(np.min(values)),
                "maximum_observation": float(np.max(values)),
                "observed_median": float(median(values)),
                "uncertainty_scale": float(uncertainty),
                "forecast_method": (
                    "recency_weighted_linear_trend"
                    if len(values) >= 3
                    else "recency_weighted_baseline"
                ),
            },
        }
