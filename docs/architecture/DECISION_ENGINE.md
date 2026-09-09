# CHARTERPULSE AI --- Decision Engine

## Objective

Turn forecasts and operational constraints into an actionable,
explainable procurement recommendation.

## Pipeline

``` text
Requirement
 -> Candidate Ports
 -> Candidate Vessels
 -> Forecast Scenarios
 -> Feasibility Filter
 -> Cost Model
 -> Optimization
 -> Risk Simulation
 -> Recommendation
```

## Recommendation actions

-   `BOOK_NOW`
-   `WAIT`
-   `CHANGE_PORT`
-   `CHANGE_VESSEL`
-   `REVIEW`

These are decision-support outputs, not guarantees.

## Cost model

Potential components: cargo cost, ocean freight, bunker/fuel, port
charges, canal charges, loading/discharge, demurrage, storage, inland
transport, insurance, delay cost and idle/repositioning cost.

## Explainability

Every recommendation should show: - selected option - alternatives -
cost/risk comparison - feasibility constraints - forecast scenario -
main drivers - data freshness - uncertainty

Never fabricate SHAP percentages or savings.

## Human loop

User can approve, modify or reject. Store the decision and reason. Later
store actual outcomes for evaluation.
