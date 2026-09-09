-- CHARTERPULSE AI
-- Physical feasibility foundation
-- Migration 029

create extension if not exists pgcrypto;

-- ============================================================
-- VESSELS
-- ============================================================

create table if not exists public.vessels (
    id uuid primary key default gen_random_uuid(),

    imo_number text unique,
    mmsi text unique,

    name text not null,

    vessel_class text,
    ship_type text,

    flag text,

    dwt_mt numeric(18,3),
    gross_tonnage numeric(18,3),

    loa_m numeric(12,3),
    beam_m numeric(12,3),
    max_draft_m numeric(12,3),

    cargo_capacity_mt numeric(18,3),

    year_built integer,

    source text,
    source_reference text,

    provenance text not null default 'REAL'
        check (provenance in (
            'REAL',
            'PUBLIC_PROXY',
            'SIMULATED',
            'USER_PROVIDED',
            'DERIVED',
            'FORECAST'
        )),

    observed_at timestamptz,

    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_vessels_class
    on public.vessels(vessel_class);

create index if not exists idx_vessels_type
    on public.vessels(ship_type);


-- ============================================================
-- PORT PHYSICAL CONSTRAINTS
-- ============================================================

create table if not exists public.port_constraints (
    id uuid primary key default gen_random_uuid(),

    port_id uuid not null
        references public.ports(id)
        on delete cascade,

    max_loa_m numeric(12,3),
    max_beam_m numeric(12,3),
    max_draft_m numeric(12,3),

    cargo_handling_types text[],

    max_vessel_capacity_mt numeric(18,3),

    loading_available boolean,
    discharge_available boolean,

    source text,
    source_reference text,

    provenance text not null default 'USER_PROVIDED'
        check (provenance in (
            'REAL',
            'PUBLIC_PROXY',
            'SIMULATED',
            'USER_PROVIDED',
            'DERIVED',
            'FORECAST'
        )),

    observed_at timestamptz,

    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),

    unique(port_id)
);

create index if not exists idx_port_constraints_port
    on public.port_constraints(port_id);


-- ============================================================
-- FEASIBILITY RUNS
-- ============================================================

create table if not exists public.feasibility_runs (
    id uuid primary key default gen_random_uuid(),

    cargo_requirement_id uuid
        references public.cargo_requirements(id)
        on delete cascade,

    vessel_id uuid
        references public.vessels(id),

    origin_port_id uuid
        references public.ports(id),

    destination_port_id uuid
        references public.ports(id),

    result text not null
        check (result in (
            'FEASIBLE',
            'INFEASIBLE',
            'REVIEW'
        )),

    cargo_capacity_ok boolean,
    cargo_compatibility_ok boolean,

    origin_loa_ok boolean,
    origin_beam_ok boolean,
    origin_draft_ok boolean,

    destination_loa_ok boolean,
    destination_beam_ok boolean,
    destination_draft_ok boolean,

    loading_capability_ok boolean,
    discharge_capability_ok boolean,

    delivery_window_ok boolean,

    reasons jsonb not null default '[]'::jsonb,
    checks jsonb not null default '{}'::jsonb,

    provenance text not null default 'DERIVED',

    created_at timestamptz not null default now()
);

create index if not exists idx_feasibility_cargo
    on public.feasibility_runs(cargo_requirement_id);

create index if not exists idx_feasibility_vessel
    on public.feasibility_runs(vessel_id);

create index if not exists idx_feasibility_result
    on public.feasibility_runs(result);


-- ============================================================
-- RLS
-- ============================================================

alter table public.vessels enable row level security;
alter table public.port_constraints enable row level security;
alter table public.feasibility_runs enable row level security;

drop policy if exists vessels_public_read
    on public.vessels;

create policy vessels_public_read
    on public.vessels
    for select
    to anon, authenticated
    using (true);

drop policy if exists port_constraints_public_read
    on public.port_constraints;

create policy port_constraints_public_read
    on public.port_constraints
    for select
    to anon, authenticated
    using (true);

drop policy if exists feasibility_runs_public_read
    on public.feasibility_runs;

create policy feasibility_runs_public_read
    on public.feasibility_runs
    for select
    to anon, authenticated
    using (true);
