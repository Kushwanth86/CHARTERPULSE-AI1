# CHARTERPULSE AI --- Data Dictionary

## Common

  -----------------------------------------------------------------------
  Field                               Meaning
  ----------------------------------- -----------------------------------
  `id`                                Unique identifier

  `source`                            Origin of record

  `source_url`                        Source location when available

  `observed_at`                       Time represented

  `ingested_at`                       Time received

  `unit`                              Measurement unit

  `provenance_type`                   REAL / PUBLIC_PROXY / USER_PROVIDED
                                      / DERIVED / FORECAST / SIMULATED

  `quality_status`                    Data quality state
  -----------------------------------------------------------------------

## Port

`name`, `unlocode`, `latitude`, `longitude`, `port_type`, `status`,
`max_draft`, `max_loa`, `max_beam`.

## Vessel

`vessel_class`, `deadweight_tonnes`, `loa`, `beam`, `draft`,
`availability_start`, `availability_end`.

## Freight observation

`route_id`, `vessel_class_id`, `rate`, `currency`, `unit`,
`observed_at`.

## Forecast

`forecast_origin`, `target_date`, `p10`, `p50`, `p90`, `model_id`,
`validation_metric`.

P10/P50/P90 are statistical forecast quantiles and must not
automatically be labelled bearish/base/bullish.
