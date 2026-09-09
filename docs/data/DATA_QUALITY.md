# CHARTERPULSE AI --- Data Quality

## Validation

-   schema/type validation
-   unit validation
-   timestamp validation
-   duplicate detection
-   physical range checks
-   missingness
-   stale-data detection
-   referential integrity
-   cross-field consistency

## Status

`VALID`, `SUSPECT`, `STALE`, `INVALID`, `MISSING`

## Freshness

Dashboard records should be able to show observed time, update time,
source and freshness.

## Missing data

Prefer another legitimate source, then a documented proxy. Model
imputation only when justified. Never silently replace missing market
data with a fixed value.

## Synthetic data

All synthetic records carry `SIMULATED`.

## Gates

Forecasting must not train on invalid records. Optimization must not
silently use invalid/stale critical constraints. Recommendations must
expose material data uncertainty.
