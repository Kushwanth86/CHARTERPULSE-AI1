-- CHARTERPULSE AI
-- Migration 025: Recover the live geography and port intelligence foundation
--
-- The original migrations 001-024 were registered remotely but contain no SQL.
-- This migration establishes the tables required by the currently implemented API.

-- ============================================================
-- COUNTRIES
-- ============================================================

CREATE TABLE IF NOT EXISTS public.countries (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    iso2 text,
    iso3 text,
    name text NOT NULL,
    source text,
    source_url text,
    observed_at timestamptz,
    updated_at timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT countries_iso2_unique UNIQUE (iso2),
    CONSTRAINT countries_iso3_unique UNIQUE (iso3)
);

CREATE INDEX IF NOT EXISTS idx_countries_name
    ON public.countries (name);

CREATE INDEX IF NOT EXISTS idx_countries_iso2
    ON public.countries (iso2);

CREATE INDEX IF NOT EXISTS idx_countries_iso3
    ON public.countries (iso3);


-- ============================================================
-- REGIONS
-- ============================================================

CREATE TABLE IF NOT EXISTS public.regions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    country_id uuid NOT NULL REFERENCES public.countries(id) ON DELETE RESTRICT,
    name text NOT NULL,
    source text,
    source_url text,
    observed_at timestamptz,
    updated_at timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT regions_country_name_unique UNIQUE (country_id, name)
);

CREATE INDEX IF NOT EXISTS idx_regions_country_id
    ON public.regions (country_id);

CREATE INDEX IF NOT EXISTS idx_regions_name
    ON public.regions (name);


-- ============================================================
-- LOCATIONS
-- ============================================================

CREATE TABLE IF NOT EXISTS public.locations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    country_id uuid NOT NULL REFERENCES public.countries(id) ON DELETE RESTRICT,
    region_id uuid REFERENCES public.regions(id) ON DELETE SET NULL,
    name text NOT NULL,
    latitude double precision,
    longitude double precision,
    timezone text,
    source text,
    source_url text,
    observed_at timestamptz,
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_locations_country_id
    ON public.locations (country_id);

CREATE INDEX IF NOT EXISTS idx_locations_region_id
    ON public.locations (region_id);

CREATE INDEX IF NOT EXISTS idx_locations_name
    ON public.locations (name);


-- ============================================================
-- PORTS
-- ============================================================

CREATE TABLE IF NOT EXISTS public.ports (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    location_id uuid NOT NULL REFERENCES public.locations(id) ON DELETE RESTRICT,
    name text NOT NULL,

    latitude double precision,
    longitude double precision,

    max_draft_m double precision,
    max_loa_m double precision,
    max_beam_m double precision,

    annual_capacity_tonnes numeric,
    storage_capacity_tonnes numeric,

    rail_connected boolean,
    road_connected boolean,
    pipeline_connected boolean,

    unlocode text,

    source text,
    source_url text,
    observed_at timestamptz,
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ports_location_id
    ON public.ports (location_id);

CREATE INDEX IF NOT EXISTS idx_ports_name
    ON public.ports (name);

CREATE INDEX IF NOT EXISTS idx_ports_unlocode
    ON public.ports (unlocode);

CREATE UNIQUE INDEX IF NOT EXISTS idx_ports_unlocode_unique
    ON public.ports (unlocode)
    WHERE unlocode IS NOT NULL;


-- ============================================================
-- TERMINALS
-- ============================================================

CREATE TABLE IF NOT EXISTS public.terminals (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    port_id uuid NOT NULL REFERENCES public.ports(id) ON DELETE RESTRICT,
    name text NOT NULL,

    source text,
    source_url text,
    observed_at timestamptz,
    updated_at timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT terminals_port_name_unique UNIQUE (port_id, name)
);

CREATE INDEX IF NOT EXISTS idx_terminals_port_id
    ON public.terminals (port_id);

CREATE INDEX IF NOT EXISTS idx_terminals_name
    ON public.terminals (name);


-- ============================================================
-- BERTHS
-- ============================================================

CREATE TABLE IF NOT EXISTS public.berths (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    terminal_id uuid NOT NULL REFERENCES public.terminals(id) ON DELETE RESTRICT,
    name text NOT NULL,

    source text,
    source_url text,
    observed_at timestamptz,
    updated_at timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT berths_terminal_name_unique UNIQUE (terminal_id, name)
);

CREATE INDEX IF NOT EXISTS idx_berths_terminal_id
    ON public.berths (terminal_id);

CREATE INDEX IF NOT EXISTS idx_berths_name
    ON public.berths (name);


-- ============================================================
-- ROW LEVEL SECURITY
-- Read-only access is required by the current public API.
-- Writes will later go through privileged ingestion services.
-- ============================================================

ALTER TABLE public.countries ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.regions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.locations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.terminals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.berths ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "public_read_countries" ON public.countries;
CREATE POLICY "public_read_countries"
    ON public.countries
    FOR SELECT
    TO anon, authenticated
    USING (true);

DROP POLICY IF EXISTS "public_read_regions" ON public.regions;
CREATE POLICY "public_read_regions"
    ON public.regions
    FOR SELECT
    TO anon, authenticated
    USING (true);

DROP POLICY IF EXISTS "public_read_locations" ON public.locations;
CREATE POLICY "public_read_locations"
    ON public.locations
    FOR SELECT
    TO anon, authenticated
    USING (true);

DROP POLICY IF EXISTS "public_read_ports" ON public.ports;
CREATE POLICY "public_read_ports"
    ON public.ports
    FOR SELECT
    TO anon, authenticated
    USING (true);

DROP POLICY IF EXISTS "public_read_terminals" ON public.terminals;
CREATE POLICY "public_read_terminals"
    ON public.terminals
    FOR SELECT
    TO anon, authenticated
    USING (true);

DROP POLICY IF EXISTS "public_read_berths" ON public.berths;
CREATE POLICY "public_read_berths"
    ON public.berths
    FOR SELECT
    TO anon, authenticated
    USING (true);


-- ============================================================
-- COMMENTS / PROVENANCE CONTRACT
-- ============================================================

COMMENT ON TABLE public.countries IS
    'Global country reference data. Source/provenance fields preserve data lineage.';

COMMENT ON TABLE public.regions IS
    'Country administrative/geographic regions.';

COMMENT ON TABLE public.locations IS
    'Global geographic locations used as the parent of ports.';

COMMENT ON TABLE public.ports IS
    'Global port intelligence foundation. Operational constraints are observational and source-backed.';

COMMENT ON TABLE public.terminals IS
    'Port terminal entities.';

COMMENT ON TABLE public.berths IS
    'Terminal berth entities.';

