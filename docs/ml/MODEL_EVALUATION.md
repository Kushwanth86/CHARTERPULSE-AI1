# CHARTERPULSE AI --- Model Evaluation

## Evaluation design

Use rolling or expanding-window time-series backtesting. Do not randomly
shuffle normal forecasting data.

## Metrics

-   MAE
-   RMSE
-   sMAPE
-   prediction interval coverage
-   interval width

## Model comparison

Where data supports it, compare: `Naive`, `Seasonal Naive`,
`ARIMA/SARIMA/ETS`, `XGBoost`.

## Leakage prevention

Do not use information that would not have existed at forecast time,
including future freight, congestion, commodity prices or actual
outcomes.

## Operational evaluation

Also measure feasibility, delivered-cost error, recommendation stability
and realized vs estimated outcomes where actual data exists.

## Monitoring

Track recent error, data drift, missingness, stale sources and interval
coverage. Retrain or downgrade models when performance materially
deteriorates.
