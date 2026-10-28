-- Restrict shared forecast reads to forecasts that satisfy the application's
-- minimum evidence contract. This intentionally fails closed for legacy/demo
-- rows and keeps the database policy aligned with forecast_evidence.py.
--
-- This is an additive corrective migration: it replaces the earlier
-- authenticated-read policy without changing forecast data or write paths.

drop policy if exists freight_forecasts_authenticated_read
  on public.freight_forecasts;

create policy freight_forecasts_authenticated_read
  on public.freight_forecasts for select to authenticated
  using (
    provenance = 'FORECAST'
    and unit = 'USD/MT'
    and origin_location_id is not null
    and destination_location_id is not null
    and origin_location_id <> destination_location_id
    and p10 >= 0
    and p50 > 0
    and p90 > 0
    and p10 <= p50
    and p50 <= p90
    and metadata->>'route_scoped' = 'true'
    and metadata->>'input_provenance' = 'MARKET_OBSERVATION'
    and jsonb_typeof(metadata->'source_provenances') = 'array'
    and metadata->'source_provenances' <> '[]'::jsonb
    and metadata->'source_provenances' <@ '["REAL", "PUBLIC_PROXY"]'::jsonb
    and jsonb_typeof(metadata->'source_labels') = 'array'
    and metadata->'source_labels' <> '[]'::jsonb
    and case
      when coalesce(metadata->>'observation_count', '') ~ '^[0-9]+$'
      then (metadata->>'observation_count')::numeric >= 3
      else false
    end
    and case
      when coalesce(metadata->>'distinct_observation_dates', '') ~ '^[0-9]+$'
      then (metadata->>'distinct_observation_dates')::numeric >= 3
      else false
    end
  );
