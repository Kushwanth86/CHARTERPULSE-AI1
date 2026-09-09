# CHARTERPULSE AI --- Data Connectors

## Purpose

Connectors isolate external data access from business logic.

## Pattern

``` python
fetch()
normalize()
validate()
attach_provenance()
persist()
```

## Groups

``` text
freight/
ports/
vessels/
weather/
commodities/
exchange_rates/
```

## Contract

A normalized record should contain source, source ID, observed time,
ingestion time, value, unit, entity/route, provenance and quality
status.

## Failure handling

If a source fails: - do not invent data - retain a last valid
observation only under an explicit freshness policy - expose source
status - prevent unusable critical inputs from silently reaching
optimization

## Security

API keys belong in environment variables/secrets, never source code.

## Testing

Each connector needs parser, validation, failure and provenance tests.
