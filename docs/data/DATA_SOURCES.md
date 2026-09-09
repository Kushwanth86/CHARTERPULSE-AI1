# CHARTERPULSE AI --- Data Sources

## Source policy

Combine public, licensed and user-provided data. A web page is not
automatically a live data feed.

## Port/location

Use UNECE UN/LOCODE for standardized trade/transport location identity.
Add physical and operational attributes from port authorities,
terminals, government datasets, recognized datasets or licensed maritime
providers.

## Freight

Prefer licensed route/vessel-class assessments where available. Public
dry-bulk indices and published historical series can be used as proxies,
but the UI must say they are proxies.

## Fuel

Use trusted public energy/bunker series or licensed maritime providers.

## Commodity and FX

Use government, recognized public or licensed market sources. Store
currency, unit and timestamp.

## Weather

Use public meteorological APIs/services or recognized providers.

## Congestion

Prefer port authorities or licensed AIS/maritime data. If current
congestion is unavailable, show the last observation and freshness.

## Vessel

Use trusted vessel specifications and licensed/public availability or
AIS data where permitted.

## Rule

For every source retain source, retrieval time, observation time, units
and transformation history. Never invent missing market values.

## Demo data

Synthetic values are allowed for tests/demo only and must be marked
`SIMULATED`.
