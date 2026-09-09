-- CHARTERPULSE AI
-- UN/LOCODE foundation
-- Source: UNECE UN/LOCODE 2025-1
--
-- Purpose:
--   1. Preserve every source record exactly enough for provenance/history.
--   2. Maintain canonical UN/LOCODE locations separately.
--   3. Do NOT equate every UN/LOCODE location with an operational port.
--
-- This migration extends the schema created by 025_schema_recovery.sql.

create table if not exists public.unlocode_source_records (
    id uuid primary key default gen_random_uuid(),

    source text not null default 'UNECE UN/LOCODE',
    source_version text not null,

    source_record_id text not null,
    record_type text not null
        check (record_type in ('LOCATION', 'HISTORY')),

    locode text,
    country_code text not null,
    location_code text,

    change_code text,
    name text,
    name_wo_diacritics text,
    subdiv text,
    function text,
    status text,
    date_code text,
    iata text,

    coordinates_raw text,
    latitude double precision,
    longitude double precision,
    coordinate_quality text not null
        check (coordinate_quality in ('VALID', 'MISSING', 'INVALID')),

    remarks text,

    source_file text,
    source_line integer,

    provenance text not null default 'REAL',

    observed_at timestamptz,
    ingested_at timestamptz not null default now(),

    constraint unlocode_source_records_source_record_unique
        unique (source, source_version, source_record_id)
);

create index if not exists idx_unlocode_source_records_locode
    on public.unlocode_source_records (locode);

create index if not exists idx_unlocode_source_records_country
    on public.unlocode_source_records (country_code);

create index if not exists idx_unlocode_source_records_version
    on public.unlocode_source_records (source_version);

create index if not exists idx_unlocode_source_records_type
    on public.unlocode_source_records (record_type);


-- Canonical UN/LOCODE identity.
-- This is an ingestion-layer canonicalization, not an assertion
-- that UNECE defines this exact selection algorithm.

create table if not exists public.unlocode_locations (
    id uuid primary key default gen_random_uuid(),

    locode text not null unique,

    country_code text not null,
    location_code text not null,

    country_id uuid references public.countries(id),

    name text not null,
    name_wo_diacritics text,

    subdiv text,
    function text,
    status text,
    date_code text,
    iata text,

    coordinates_raw text,
    latitude double precision,
    longitude double precision,
    coordinate_quality text not null
        check (coordinate_quality in ('VALID', 'MISSING', 'INVALID')),

    canonical_source_record_id uuid
        references public.unlocode_source_records(id),

    source text not null default 'UNECE UN/LOCODE',
    source_version text not null,
    provenance text not null default 'REAL',

    observed_at timestamptz,
    updated_at timestamptz not null default now()
);

create index if not exists idx_unlocode_locations_country
    on public.unlocode_locations (country_code);

create index if not exists idx_unlocode_locations_country_id
    on public.unlocode_locations (country_id);

create index if not exists idx_unlocode_locations_subdiv
    on public.unlocode_locations (country_code, subdiv);

create index if not exists idx_unlocode_locations_function
    on public.unlocode_locations (function);


-- Relationship table preserving duplicate/history relationships
-- without pretending they are separate physical locations.

create table if not exists public.unlocode_source_relationships (
    id uuid primary key default gen_random_uuid(),

    locode text not null,
    canonical_source_record_id uuid
        references public.unlocode_source_records(id),
    related_source_record_id uuid
        references public.unlocode_source_records(id),

    relationship text not null
        check (relationship in ('CANONICAL', 'DUPLICATE', 'HISTORY')),

    source text not null default 'UNECE UN/LOCODE',
    source_version text not null,

    observed_at timestamptz,
    created_at timestamptz not null default now(),

    unique (
        locode,
        canonical_source_record_id,
        related_source_record_id,
        relationship
    )
);


-- Link canonical UN/LOCODE identity to the existing operational
-- locations table without making UN/LOCODE itself the operational
-- port model.

alter table public.locations
    add column if not exists unlocode text;

alter table public.locations
    add column if not exists unlocode_source_record_id uuid;

alter table public.locations
    add column if not exists name_wo_diacritics text;

alter table public.locations
    add column if not exists subdiv text;

alter table public.locations
    add column if not exists function text;

alter table public.locations
    add column if not exists status text;

alter table public.locations
    add column if not exists iata text;

alter table public.locations
    add column if not exists coordinates_raw text;

alter table public.locations
    add column if not exists coordinate_quality text;

alter table public.locations
    add column if not exists source_version text;

create unique index if not exists uq_locations_unlocode
    on public.locations (unlocode)
    where unlocode is not null;

create index if not exists idx_locations_subdiv
    on public.locations (country_id, subdiv);

create index if not exists idx_locations_function
    on public.locations (function);


-- Public read access is appropriate for the public geographic dataset.
-- Writes should later be performed by the privileged ingestion service,
-- not by arbitrary public clients.

alter table public.unlocode_source_records enable row level security;
alter table public.unlocode_locations enable row level security;
alter table public.unlocode_source_relationships enable row level security;

drop policy if exists "unlocode_source_records_public_read"
    on public.unlocode_source_records;

create policy "unlocode_source_records_public_read"
    on public.unlocode_source_records
    for select
    to anon, authenticated
    using (true);

drop policy if exists "unlocode_locations_public_read"
    on public.unlocode_locations;

create policy "unlocode_locations_public_read"
    on public.unlocode_locations
    for select
    to anon, authenticated
    using (true);

drop policy if exists "unlocode_source_relationships_public_read"
    on public.unlocode_source_relationships;

create policy "unlocode_source_relationships_public_read"
    on public.unlocode_source_relationships
    for select
    to anon, authenticated
    using (true);