# CHARTERPULSE AI --- Forecasting

## Goal

Forecast freight-related metrics by vessel class and trade lane to
support charter timing.

## Model ladder

``` text
Naive -> Seasonal Naive -> ARIMA/SARIMA/ETS -> XGBoost/Gradient Boosting -> Advanced model only if justified
```

Complexity must be earned by backtesting.

## Horizons

Support short, medium and longer horizons according to available data
and procurement decisions.

## Features

Freight lags, rolling statistics, volatility, fuel, commodity
indicators, FX, historically learned seasonality, congestion and
weather/disruption variables.

## Uncertainty

Return P10/P50/P90 where supported. Conformal prediction may be used for
calibrated intervals.

## Evaluation

Use time-aware backtesting. Metrics: - MAE - RMSE - sMAPE - prediction
interval coverage - interval width

## Baseline

Every advanced model must be compared with a persistence/naive baseline.

## Output

Route, vessel class, forecast origin, target dates, P10/P50/P90, model,
validation metric and data freshness.

## Limitation

Freight markets can be difficult to predict. Forecasts are decision
support, not certainty.
