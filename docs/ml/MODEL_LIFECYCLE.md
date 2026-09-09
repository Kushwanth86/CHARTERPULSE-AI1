# CHARTERPULSE AI — Model Lifecycle

## 1. Purpose

This document defines how forecasting and other ML models move from data preparation to production, evaluation, and improvement.

The lifecycle is designed for decision intelligence: a model is useful only when its predictions are accurate enough, sufficiently fresh, appropriately uncertain, and safe to use in the decision workflow.

## 2. Lifecycle

```text
Data Sources
    ↓
Ingestion
    ↓
Validation
    ↓
Feature Engineering
    ↓
Training
    ↓
Backtesting
    ↓
Model Comparison
    ↓
Registration
    ↓
Approval
    ↓
Deployment
    ↓
Inference
    ↓
Monitoring
    ↓
Outcome Evaluation
    ↓
Retraining / Retirement
```

## 3. Data Readiness

Before training, the pipeline should validate:

- source provenance
- observation timestamps
- units
- missingness
- duplicates
- outliers
- geographic scope
- target availability
- feature availability
- temporal ordering

Training data must not contain future information that would be unavailable at prediction time.

## 4. Training

Training pipelines should record:

- dataset/version
- feature version
- target
- model type
- hyperparameters
- training period
- code version
- random seed where applicable
- training timestamp

Training should be reproducible from recorded inputs and configuration.

## 5. Evaluation

Time-series models must be evaluated using time-aware backtesting.

Minimum metrics include:

- MAE
- RMSE
- MAPE or sMAPE where appropriate
- forecast bias
- prediction interval coverage

Model selection must compare against a simple baseline. A complex model is not accepted solely because it is more sophisticated.

## 6. Prediction Intervals

When the model provides probabilistic forecasts, validate whether prediction intervals achieve their intended coverage.

For example, a nominal 90% interval should be evaluated against observed outcomes rather than assumed to be 90% accurate.

## 7. Model Registry

Each registered model should contain:

```text
model_id
model_name
model_type
target
version
status
training_dataset
feature_version
training_period
validation_period
metrics
interval_method
created_at
approved_at
retired_at
code_version
```

Recommended statuses:

- DEVELOPMENT
- VALIDATION
- CANDIDATE
- PRODUCTION
- DEPRECATED
- RETIRED

## 8. Promotion Rules

A candidate model may be promoted only when:

1. data validation passes;
2. backtesting completes;
3. required metrics are recorded;
4. the model improves or provides a justified trade-off against the baseline;
5. prediction uncertainty is evaluated where applicable;
6. inference behavior is validated;
7. the model is approved for production use.

## 9. Inference

Production inference should record:

- model ID/version
- input data timestamp
- prediction timestamp
- prediction values
- prediction interval
- data quality state
- provenance

The system should distinguish observed values from forecasts at the data/API/UI level.

## 10. Monitoring

Monitor at least four areas:

### Data quality

- missing values
- schema changes
- invalid values
- freshness
- source availability

### Data drift

Track meaningful changes in feature distributions and data coverage.

### Model accuracy

When actual outcomes become available, compare them with prior predictions.

### Operational health

Track inference failures, latency, and pipeline failures.

## 11. Prediction → Outcome Feedback

The core feedback loop is:

```text
Prediction
    ↓
Recommendation
    ↓
Human Decision
    ↓
Actual Outcome
    ↓
Prediction Error
    ↓
Model Evaluation
```

This allows CHARTERPULSE to measure whether its recommendations actually improve decisions rather than only reporting offline model metrics.

## 12. Retraining Triggers

Retraining may be considered when:

- accuracy degrades beyond an approved threshold;
- meaningful feature or target drift occurs;
- new high-quality historical data becomes available;
- market structure changes materially;
- a new feature source is validated;
- scheduled model review requires reevaluation.

Retraining must still pass the same validation and promotion process.

## 13. Rollback

A previous production model must remain identifiable and recoverable. If a newly promoted model behaves incorrectly, the system should support reverting to the last approved production version or baseline.

## 14. Model Retirement

Models should be retired when:

- their data source is discontinued;
- the target definition changes;
- accuracy becomes unacceptable;
- a validated replacement is superior;
- the model is outside its intended operating domain.

Retired models should remain in historical records so past predictions and decisions remain traceable.

## 15. Governance

Model outputs are decision support. Production workflows must preserve human approval and must not treat an ML prediction as an autonomous charter execution instruction.

Model metadata, prediction provenance, human decisions, and actual outcomes should remain linked for auditability and future evaluation.
