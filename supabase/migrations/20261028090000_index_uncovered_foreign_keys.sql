-- Add covering indexes for foreign keys identified by Supabase's performance advisor.
-- These indexes improve join/delete/update checks without changing row semantics.
create index if not exists idx_cargo_requirements_destination_location_fk
  on public.cargo_requirements (destination_location_id);
create index if not exists idx_cargo_requirements_origin_location_fk
  on public.cargo_requirements (origin_location_id);
create index if not exists idx_decision_outcomes_human_decision_fk
  on public.decision_outcomes (human_decision_id);
create index if not exists idx_feasibility_runs_destination_port_fk
  on public.feasibility_runs (destination_port_id);
create index if not exists idx_feasibility_runs_origin_port_fk
  on public.feasibility_runs (origin_port_id);
create index if not exists idx_freight_forecasts_destination_location_fk
  on public.freight_forecasts (destination_location_id);
create index if not exists idx_market_observations_destination_location_fk
  on public.market_observations (destination_location_id);
create index if not exists idx_unlocode_locations_canonical_source_record_fk
  on public.unlocode_locations (canonical_source_record_id);
create index if not exists idx_unlocode_source_relationships_canonical_source_record_fk
  on public.unlocode_source_relationships (canonical_source_record_id);
create index if not exists idx_unlocode_source_relationships_related_source_record_fk
  on public.unlocode_source_relationships (related_source_record_id);
