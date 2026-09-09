# CHARTERPULSE AI --- System Architecture

## Purpose

CHARTERPULSE AI is a decision-support platform for bulk maritime
procurement and vessel chartering. The primary SIH26006 use case is to
move from reactive market checking toward forecast-driven charter
timing, vessel selection, port selection, cost and risk decisions.

## End-to-end flow

``` text
Cargo Requirement
 -> Real/Proxy Data
 -> Validation + Provenance
 -> Supabase
 -> Market/Port/Vessel Intelligence
 -> Freight Forecast
 -> P10/P50/P90
 -> Port + Vessel + Cargo Feasibility
 -> Route/Charter Options
 -> Total Delivered Cost
 -> Optimization
 -> Risk / What-If
 -> Explainable Recommendation
 -> Human Decision
 -> Actual Outcome
 -> Evaluation / Feedback
```

## Components

-   `apps/web`: React + TypeScript decision dashboard.
-   `services/api`: FastAPI orchestration and business API.
-   `ml`: forecasting, backtesting and monitoring.
-   `optimization`: constrained charter/shipment optimization.
-   `risk`: scenario, sensitivity and Monte Carlo analysis.
-   `supabase`: operational database and provenance.
-   `tests`: unit, integration and end-to-end validation.

## Principles

1.  Real data where available.
2.  Every important observation has source and timestamp.
3.  Synthetic data is explicitly labelled.
4.  Forecasts include uncertainty.
5.  Physical feasibility is checked before optimization.
6.  Recommendations are explainable.
7.  Human decisions and actual outcomes are stored.
8.  No hard-coded market prices, confidence or tiny fixed port lists.
9.  Global port architecture is supported; SIH26006 remains the first
    target.
