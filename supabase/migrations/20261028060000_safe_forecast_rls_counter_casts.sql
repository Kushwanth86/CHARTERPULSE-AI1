-- Make forecast evidence RLS evaluation safe for malformed JSON counters.
-- PostgreSQL may reorder AND predicates, so a regex check next to an integer
-- cast is not a sufficient guard against cast exceptions. CASE ensures casts
-- are only evaluated after the input has been bounded and validated.

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
      when coalesce(metadata->>'observation_count', '') ~ '^[0-9]{1,3}$'
      then (metadata->>'observation_count')::integer between 3 and 500
      else false
    end
    and case
      when coalesce(metadata->>'distinct_observation_dates', '') ~ '^[0-9]{1,3}$'
      then (metadata->>'distinct_observation_dates')::integer between 3 and 500
      else false
    end
    and case
      when coalesce(metadata->>'observation_count', '') ~ '^[0-9]{1,3}$'
       and coalesce(metadata->>'distinct_observation_dates', '') ~ '^[0-9]{1,3}$'
      then (metadata->>'distinct_observation_dates')::integer
           <= (metadata->>'observation_count')::integer
      else false
    end
  );
