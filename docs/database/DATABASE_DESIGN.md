# CHARTERPULSE AI --- Database Design

## Database

Supabase PostgreSQL.

## Core tables

### Geography

`countries`, `regions`, `locations`

### Ports

`ports`, `terminals`, `berths`, `port_capabilities`, `port_constraints`,
`port_capacity`, `port_operations`, `port_congestion`

### Cargo

`cargo_types`, `cargo_requirements`

### Vessels

`vessel_classes`, `vessels`, `vessel_availability`

### Market

`routes`, `freight_observations`, `fuel_observations`,
`commodity_observations`, `exchange_rate_observations`,
`weather_observations`

### AI / procurement

`procurement_requests`, `forecasts`, `optimization_runs`, `risk_runs`,
`decisions`, `outcomes`, `feedback`

### Governance

`data_provenance`, `audit_logs`

## Principles

Use foreign keys, preserve observations, separate reference data from
time-series observations, index route/port/vessel/time, store units and
use RLS where appropriate.

## Forecast record

Link target metric, route, vessel class, forecast origin, horizon,
P10/P50/P90, model identifier, source dataset and creation time.

## Outcome

Capture actual freight, delay, demurrage, delivered cost, arrival and
notes so forecasts and recommendations can be evaluated.
