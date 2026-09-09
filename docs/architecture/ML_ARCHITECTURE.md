# CHARTERPULSE AI — Machine Learning Architecture

## 1. Purpose

This document defines the machine-learning architecture for CHARTERPULSE AI. ML is used to improve forecasting, uncertainty estimation, anomaly detection, and decision support. ML does not replace physical feasibility rules, optimization constraints, or human approval.

## 2. Decision Context

The primary decision is:

> Given a cargo requirement today, should the organization charter now or later, which feasible transportation option should be selected, and which strategy minimizes expected total delivered cost and risk?

ML supplies predictions and uncertainty to that decision engine.

## 3. ML Flow

```text
External / Internal Data
        ↓
Raw Ingestion
        ↓
Parsing + Normalization
        ↓
Data Quality Validation
        ↓
Provenance + Freshness
        ↓
Feature Engineering
        ↓
Baseline Models
        ↓
Statistical Models
        ↓
Machine Learning Models
        ↓
Backtesting + Model Comparison
        ↓
Forecast + Prediction Interval
        ↓
Decision / Optimization Engine
        ↓
Human Decision
        ↓
Actual Outcome
        ↓
Model Evaluation
```

## 4. Forecasting Strategy

CHARTERPULSE should compare models instead of assuming that a complex model is automatically better.

### Required model tiers

1. Naive baseline
2. Seasonal naive baseline
3. Exponential smoothing
4. ARIMA / SARIMA where appropriate
5. Tree-based ML such as gradient boosting, XGBoost, or random forest when explanatory features justify it
6. Ensemble models when validation demonstrates improvement

Deep learning models such as LSTM or Transformer architectures are optional and must only be introduced when sufficient historical data and validation evidence justify them.

## 5. Forecast Targets

The architecture supports multiple forecast targets without hard-coding a single commodity or route:

- freight rate
- bunker/fuel cost
- port congestion or delay
- transit time
- vessel availability indicators
- commodity demand indicators
- delivered logistics cost components

Each target must identify its unit, geography, route or market scope, observation timestamp, source, and provenance.

## 6. Features

Potential feature groups include:

- historical freight observations
- commodity and cargo characteristics
- origin and destination geography
- port characteristics
- vessel class and capacity
- seasonality
- congestion
- weather-derived indicators
- bunker/fuel prices
- exchange rates
- trade-flow indicators
- vessel availability observations
- calendar effects

Features must be derived from validated source data. Missing values must not silently become invented market values.

## 7. Uncertainty

Every production forecast should expose uncertainty when sufficient data exists.

Preferred representations include:

- P10
- P50
- P90
- prediction interval
- interval coverage during validation
- forecast horizon
- model version
- data freshness

A confidence value must be calculated from model/data quality and validation evidence. It must not be a manually invented percentage.

## 8. Model Evaluation

Minimum evaluation metrics:

- MAE
- RMSE
- MAPE or sMAPE where mathematically appropriate
- prediction interval coverage
- forecast bias

Evaluation must use time-aware backtesting. Random train/test splitting is not appropriate for ordinary time-series forecasting.

## 9. Model Selection

The model registry should retain:

- model identifier
- model type
- target
- feature set/version
- training data period
- validation period
- metrics
- prediction interval method
- training timestamp
- code/version identifier
- status

A more complex model must demonstrate measurable improvement over the baseline before becoming the production model.

## 10. Inference Contract

Forecast inference should return at minimum:

```text
forecast_id
entity / route / market scope
target
horizon
P10
P50
P90
point_forecast
model_id
model_version
observed_at
forecast_created_at
source/provenance
quality_status
```

## 11. Data Quality and Provenance

Every ML input should preserve provenance using the project vocabulary:

- REAL
- PUBLIC_PROXY
- SIMULATED
- USER_PROVIDED
- DERIVED
- FORECAST

The system must retain source timestamps and freshness. A stale observation should be marked stale rather than presented as live.

## 12. Explainability

For tree-based models, SHAP or equivalent feature-attribution methods may be used. Explanations must be generated from actual model outputs. The system must never manufacture contribution percentages merely to make a recommendation look explainable.

## 13. Failure Handling

If data is insufficient, stale, inconsistent, or outside the validated model domain:

1. mark the data/model quality state;
2. fall back to an approved baseline where possible;
3. expose the limitation to the decision engine;
4. avoid false precision;
5. allow human review.

## 14. Lifecycle

```text
Ingest → Validate → Train → Backtest → Register → Deploy → Monitor → Evaluate → Improve
```

Retraining should be driven by data availability, accuracy degradation, drift, or a planned model-review cycle rather than blindly retraining on every ingestion.

## 15. Integration Boundaries

ML must not bypass:

- cargo compatibility rules
- vessel compatibility rules
- port constraints
- route feasibility
- delivery deadlines
- optimization constraints
- risk controls
- human approval

The ML layer provides evidence. The decision engine combines evidence with deterministic constraints and optimization results.
