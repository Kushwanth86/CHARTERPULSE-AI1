# CHARTERPULSE AI --- Data Architecture

## Data flow

``` text
External Sources -> Connectors -> Raw Observations -> Validation
-> Normalization -> Feature Engineering -> Supabase
-> Forecast / Feasibility / Optimization -> Decision -> Outcome
```

## Domains

-   geography and locations
-   ports, terminals and berths
-   cargo taxonomy and requirements
-   vessel classes/specifications/availability
-   routes
-   freight, fuel, commodity and FX observations
-   weather and congestion
-   forecasts
-   procurement and charter decisions
-   actual outcomes and feedback
-   provenance and audit data

## Static vs time-varying

Slow-changing: location identity, coordinates, vessel dimensions, cargo
taxonomy. Time-varying: freight, fuel, congestion, weather, vessel
availability, commodity prices, forecasts.

Historical observations must not be overwritten.

## Provenance

Every important record should carry `source`, `source_url` when
available, `observed_at`, `ingested_at`, `unit`, `provenance_type`, and
`quality_status`.

Supported types: `REAL`, `PUBLIC_PROXY`, `USER_PROVIDED`, `DERIVED`,
`FORECAST`, `SIMULATED`.

## Global ports

``` text
Country -> Region -> Location -> Port -> Terminal -> Berth
```

UN/LOCODE is the global location identity layer where applicable. Live
operational constraints require additional sources.

## Feature engineering

Possible features include freight lags, rolling volatility, historically
learned seasonality, fuel, commodity, FX, route characteristics,
congestion and weather/disruption indicators. Do not invent seasonality.
