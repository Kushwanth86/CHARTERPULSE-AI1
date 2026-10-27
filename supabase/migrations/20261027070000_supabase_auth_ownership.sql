-- Supabase Auth ownership and private-data access controls.
-- User-owned rows remain nullable for the pre-auth historical dataset; legacy
-- rows with no owner are intentionally not visible through authenticated APIs.

alter table public.cargo_requirements
  add column if not exists user_id uuid references auth.users(id) on delete cascade;
alter table public.decision_runs
  add column if not exists user_id uuid references auth.users(id) on delete cascade;
alter table public.human_decisions
  add column if not exists user_id uuid references auth.users(id) on delete cascade;
alter table public.decision_outcomes
  add column if not exists user_id uuid references auth.users(id) on delete cascade;
alter table public.decision_feedback
  add column if not exists user_id uuid references auth.users(id) on delete cascade;
alter table public.feasibility_runs
  add column if not exists user_id uuid references auth.users(id) on delete cascade;
alter table public.market_observations
  add column if not exists user_id uuid references auth.users(id) on delete cascade;
alter table public.model_evaluations
  add column if not exists user_id uuid references auth.users(id) on delete cascade;
alter table public.vessels
  add column if not exists user_id uuid references auth.users(id) on delete cascade;
alter table public.vessel_cargo_compatibility
  add column if not exists user_id uuid references auth.users(id) on delete cascade;

create index if not exists idx_cargo_requirements_user_created
  on public.cargo_requirements (user_id, created_at desc);
create index if not exists idx_decision_runs_user_created
  on public.decision_runs (user_id, created_at desc);
create index if not exists idx_human_decisions_user_decided
  on public.human_decisions (user_id, decided_at desc);
create index if not exists idx_decision_outcomes_user_recorded
  on public.decision_outcomes (user_id, recorded_at desc);
create index if not exists idx_decision_feedback_user_created
  on public.decision_feedback (user_id, created_at desc);
create index if not exists idx_feasibility_runs_user_created
  on public.feasibility_runs (user_id, created_at desc);
create index if not exists idx_market_observations_user_observed
  on public.market_observations (user_id, observed_at desc);
create index if not exists idx_model_evaluations_user_evaluated
  on public.model_evaluations (user_id, evaluated_at desc);
create index if not exists idx_vessels_user_created
  on public.vessels (user_id, created_at desc);
create index if not exists idx_vessel_cargo_compatibility_user_created
  on public.vessel_cargo_compatibility (user_id, created_at desc);

-- Remove unrestricted anonymous/authenticated read policies from private data.
drop policy if exists cargo_requirements_public_read on public.cargo_requirements;
drop policy if exists decision_runs_public_read on public.decision_runs;
drop policy if exists human_decisions_public_read on public.human_decisions;
drop policy if exists public_read_decision_outcomes on public.decision_outcomes;
drop policy if exists public_read_decision_feedback on public.decision_feedback;
drop policy if exists feasibility_runs_public_read on public.feasibility_runs;
drop policy if exists public_read_model_evaluations on public.model_evaluations;
drop policy if exists market_observations_public_read on public.market_observations;
drop policy if exists public_read_market_observations on public.market_observations;
drop policy if exists vessels_public_read on public.vessels;
drop policy if exists vessel_cargo_compatibility_public_read on public.vessel_cargo_compatibility;
drop policy if exists freight_forecasts_public_read on public.freight_forecasts;
drop policy if exists public_read_freight_forecasts on public.freight_forecasts;

-- Defense in depth: anonymous users cannot query operational data even if a
-- legacy SELECT policy survives, and browser sessions cannot write directly.
-- The API uses the server-only service role for data access; authenticated
-- direct reads, where granted below, remain subject to the ownership RLS rules.
revoke select on table
  public.cargo_requirements,
  public.decision_runs,
  public.human_decisions,
  public.decision_outcomes,
  public.decision_feedback,
  public.feasibility_runs,
  public.market_observations,
  public.freight_forecasts,
  public.model_evaluations,
  public.vessels,
  public.vessel_cargo_compatibility
from anon;

revoke insert, update, delete, truncate on table
  public.cargo_requirements,
  public.decision_runs,
  public.human_decisions,
  public.decision_outcomes,
  public.decision_feedback,
  public.feasibility_runs,
  public.market_observations,
  public.freight_forecasts,
  public.model_evaluations,
  public.vessels,
  public.vessel_cargo_compatibility
from anon, authenticated;

-- No direct Data API writes are granted by this migration. Writes happen only
-- through authenticated backend routes, which set user_id from the verified JWT
-- rather than trusting a caller-supplied owner ID.
create policy cargo_requirements_select_own
  on public.cargo_requirements for select to authenticated
  using ((select auth.uid()) = user_id);
create policy decision_runs_select_own
  on public.decision_runs for select to authenticated
  using ((select auth.uid()) = user_id);
create policy human_decisions_select_own
  on public.human_decisions for select to authenticated
  using ((select auth.uid()) = user_id);
create policy decision_outcomes_select_own
  on public.decision_outcomes for select to authenticated
  using ((select auth.uid()) = user_id);
create policy decision_feedback_select_own
  on public.decision_feedback for select to authenticated
  using ((select auth.uid()) = user_id);
create policy feasibility_runs_select_own
  on public.feasibility_runs for select to authenticated
  using ((select auth.uid()) = user_id);
create policy model_evaluations_select_own
  on public.model_evaluations for select to authenticated
  using ((select auth.uid()) = user_id);

-- Market observations and vessel catalog rows may contain shared, trusted
-- provider data. Users may also see their own USER_PROVIDED rows, never another
-- user's entries or anonymous users' data.
create policy market_observations_authenticated_read
  on public.market_observations for select to authenticated
  using (
    provenance in ('REAL', 'PUBLIC_PROXY')
    or (select auth.uid()) = user_id
  );
create policy vessels_authenticated_read
  on public.vessels for select to authenticated
  using (
    provenance in ('REAL', 'PUBLIC_PROXY')
    or (select auth.uid()) = user_id
  );
create policy vessel_cargo_compatibility_authenticated_read
  on public.vessel_cargo_compatibility for select to authenticated
  using (
    provenance in ('REAL', 'PUBLIC_PROXY')
    or (select auth.uid()) = user_id
  );

-- Market forecasts derived from trusted/shared data are common to authenticated
-- app users, but must not be available to anonymous visitors.
create policy freight_forecasts_authenticated_read
  on public.freight_forecasts for select to authenticated
  using (true);

comment on column public.cargo_requirements.user_id is 'Supabase Auth owner of this procurement requirement; NULL legacy rows are private/unassigned.';
comment on column public.decision_runs.user_id is 'Supabase Auth owner of this decision run.';
comment on column public.market_observations.user_id is 'Supabase Auth owner for caller-submitted observations; trusted provider observations may remain NULL.';
