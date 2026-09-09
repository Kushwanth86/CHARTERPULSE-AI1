# CHARTERPULSE AI --- Data Provenance

## Types

-   `REAL`: direct observation from an identified source.
-   `PUBLIC_PROXY`: public metric used as a proxy.
-   `USER_PROVIDED`: entered/uploaded by a user.
-   `DERIVED`: calculated from other records.
-   `FORECAST`: model output.
-   `SIMULATED`: testing/demo value.

## Required metadata

`provenance_type`, `source`, `source_url`, `observed_at`, `ingested_at`,
transformation notes, input record IDs and quality status.

## UI rules

Distinguish observed vs forecast, proxy vs direct market data, and
simulated vs operational data. Show freshness for important metrics.

## No false precision

A forecast is not a fact. Estimated savings are not realized savings. A
proxy is not a licensed route-specific freight assessment.
