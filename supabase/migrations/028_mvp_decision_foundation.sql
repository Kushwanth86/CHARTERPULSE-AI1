-- CHARTERPULSE AI
-- MVP vertical-slice foundation
-- Migration 028

create extension if not exists pgcrypto;

-- ============================================================
-- CARGO REQUIREMENTS
-- ============================================================

create table if not exists public.cargo_requirements (
    id uuid primary key default gen_random_uuid(),

    cargo_type text,
    material text not null,

    quantity_mt numeric(18,3) not null
        check (quantity_mt > 0),

    origin_location_id uuid references public.locations(id),
    destination_location_id uuid references public.locations(id),

    earliest_delivery timestamptz,
    latest_delivery timestamptz,

    priority text not null default 'NORMAL'
        check (priority in ('LOW', 'NORMAL', 'HIGH', 'CRITICAL')),

    status text not null default 'DRAFT'
        check (status in (
            'DRAFT',
            'SUBMITTED',
            'ANALYZING',
            'RECOMMENDED',
            'APPROVED',
            'REJECTED',
            'COMPLETED',
            'CANCELLED'
        )),

    provenance text not null default 'USER_PROVIDED',

    source text,
    source_reference text,

    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_cargo_requirements_status
    on public.cargo_requirements(status);

create index if not exists idx_cargo_requirements_material
    on public.cargo_requirements(material);

create index if not exists idx_cargo_requirements_delivery
    on public.cargo_requirements(latest_delivery);


-- ============================================================
-- MARKET OBSERVATIONS
-- ============================================================

create table if not exists public.market_observations (
    id uuid primary key default gen_random_uuid(),

    market_type text not null,
    metric text not null,

    origin_location_id uuid references public.locations(id),
    destination_location_id uuid references public.locations(id),

    vessel_class text,

    value numeric(20,6) not null,
    unit text not null,
    currency text,

    observed_at timestamptz not null,

    source text not null,
    source_reference text,

    provenance text not null
        check (provenance in (
            'REAL',
            'PUBLIC_PROXY',
            'SIMULATED',
            'USER_PROVIDED',
            'DERIVED',
            'FORECAST'
        )),

    created_at timestamptz not null default now()
);

create index if not exists idx_market_observations_metric
    on public.market_observations(metric);

create index if not exists idx_market_observations_observed
    on public.market_observations(observed_at);

create index if not exists idx_market_observations_route
    on public.market_observations(
        origin_location_id,
        destination_location_id
    );


-- ============================================================
-- FREIGHT FORECASTS
-- ============================================================

create table if not exists public.freight_forecasts (
    id uuid primary key default gen_random_uuid(),

    origin_location_id uuid references public.locations(id),
    destination_location_id uuid references public.locations(id),

    vessel_class text,

    forecast_horizon_days integer
        check (forecast_horizon_days >= 0),

    p10 numeric(20,6),
    p50 numeric(20,6),
    p90 numeric(20,6),

    unit text not null,
    currency text,

    baseline_value numeric(20,6),

    model_name text not null,
    model_version text,

    mae numeric(20,6),
    rmse numeric(20,6),
    smape numeric(20,6),

    interval_coverage numeric(10,6),

    confidence numeric(10,6)
        check (confidence >= 0 and confidence <= 1),

    provenance text not null default 'FORECAST',

    generated_at timestamptz not null default now(),

    metadata jsonb not null default '{}'::jsonb
);

create index if not exists idx_freight_forecasts_route
    on public.freight_forecasts(
        origin_location_id,
        destination_location_id
    );

create index if not exists idx_freight_forecasts_generated
    on public.freight_forecasts(generated_at);


-- ============================================================
-- DECISION RUNS
-- ============================================================

create table if not exists public.decision_runs (
    id uuid primary key default gen_random_uuid(),

    cargo_requirement_id uuid
        references public.cargo_requirements(id)
        on delete cascade,

    recommendation text not null
        check (recommendation in (
            'CHARTER_NOW',
            'WAIT',
            'CHANGE_PORT',
            'REVIEW'
        )),

    recommendation_score numeric(10,6),

    expected_total_cost numeric(20,6),
    expected_cost_unit text,
    expected_cost_currency text,

    risk_score numeric(10,6),
    confidence numeric(10,6),

    rationale text,

    forecast_snapshot jsonb not null default '{}'::jsonb,
    feasibility_snapshot jsonb not null default '{}'::jsonb,
    cost_snapshot jsonb not null default '{}'::jsonb,
    risk_snapshot jsonb not null default '{}'::jsonb,
    optimization_snapshot jsonb not null default '{}'::jsonb,

    provenance text not null default 'DERIVED',

    created_at timestamptz not null default now()
);

create index if not exists idx_decision_runs_cargo
    on public.decision_runs(cargo_requirement_id);

create index if not exists idx_decision_runs_created
    on public.decision_runs(created_at);


-- ============================================================
-- HUMAN DECISION
-- ============================================================

create table if not exists public.human_decisions (
    id uuid primary key default gen_random_uuid(),

    decision_run_id uuid not null
        references public.decision_runs(id)
        on delete cascade,

    action text not null
        check (action in (
            'APPROVE',
            'MODIFY',
            'REJECT'
        )),

    modified_parameters jsonb not null default '{}'::jsonb,

    reason text,

    decided_at timestamptz not null default now(),

    actor_reference text,

    provenance text not null default 'USER_PROVIDED'
);

create index if not exists idx_human_decisions_run
    on public.human_decisions(decision_run_id);


-- ============================================================
-- RLS
-- ============================================================

alter table public.cargo_requirements enable row level security;
alter table public.market_observations enable row level security;
alter table public.freight_forecasts enable row level security;
alter table public.decision_runs enable row level security;
alter table public.human_decisions enable row level security;

-- Development read policies.
-- Writes will be performed by the trusted API using the server key.

drop policy if exists cargo_requirements_public_read
    on public.cargo_requirements;

create policy cargo_requirements_public_read
    on public.cargo_requirements
    for select
    to anon, authenticated
    using (true);

drop policy if exists market_observations_public_read
    on public.market_observations;

create policy market_observations_public_read
    on public.market_observations
    for select
    to anon, authenticated
    using (true);

drop policy if exists freight_forecasts_public_read
    on public.freight_forecasts;

create policy freight_forecasts_public_read
    on public.freight_forecasts
    for select
    to anon, authenticated
    using (true);

drop policy if exists decision_runs_public_read
    on public.decision_runs;

create policy decision_runs_public_read
    on public.decision_runs
    for select
    to anon, authenticated
    using (true);

drop policy if exists human_decisions_public_read
    on public.human_decisions;

create policy human_decisions_public_read
    on public.human_decisions
    for select
    to anon, authenticated
    using (true);
