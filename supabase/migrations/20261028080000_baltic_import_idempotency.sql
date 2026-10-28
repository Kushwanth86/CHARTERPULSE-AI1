-- Make Baltic Exchange imports idempotent even when two importer processes
-- overlap. The partial unique index avoids changing uniqueness semantics for
-- existing simulated/user-submitted observations.
create unique index if not exists uq_market_observations_baltic_source_reference
  on public.market_observations (source_reference)
  where source_reference like 'baltic-exchange:%';
