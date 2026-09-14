-- CHARTERPULSE AI
-- Migration 027: Restore the operational tables required by the current MVP API.
--
-- Migrations 001-024 were registered remotely but did not contain the original
-- table definitions. Migration 025 restored geography/port intelligence and
-- 026 restored the UN/LOCODE foundation. This migration restores the next
-- dependency layer used by the cargo, vessel and feasibility APIs.
--
-- No synthetic market values are inserted here. These are schema definitions only.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============================================================
-- CARGO REQUIREMENTS
-- ============================================================

CREATE TABLE IF NOT EXISTS public.cargo_requirements (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    cargo_type text,
    material text NOT NULL,
    quantity_mt double precision NOT NULL CHECK (quantity_mt > 0),

    origin_location_id uuid REFERENCES public.locations(id) ON DELETE SET NULL,
    destination_location_id uuid REFERENCES public.locations(id) ON DELETE SET NULL,

    earliest_delivery timestamptz,
    latest_delivery timestamptz,
    priority text NOT NULL DEFAULT 'NORMAL',
    status text NOT NULL DEFAULT 'OPEN',

    provenance text NOT NULL DEFAULT 'USER_PROVIDED',
    source text,
    source_reference text,

    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_cargo_requirements_created_at
    ON public.cargo_requirements (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_cargo_requirements_material
    ON public.cargo_requirements (material);

CREATE INDEX IF NOT EXISTS idx_cargo_requirements_status
    ON public.cargo_requirements (status);


-- ============================================================
-- VESSELS
-- ============================================================

CREATE TABLE IF NOT EXISTS public.vessels (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),

    imo_number text,
    mmsi text,
    name text NOT NULL,

    vessel_class text,
    ship_type text,
    flag text,

    dwt_mt double precision,
    gross_tonnage double precision,

    loa_m double precision,
    beam_m double precision,
    max_draft_m double precision,

    cargo_capacity_mt double precision,

    year_built integer,

    source text,
    source_reference text,
    provenance text NOT NULL DEFAULT 'USER_PROVIDED',
    observed_at timestamptz,

    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_vessels_imo_number
    ON public.vessels (imo_number)
    WHERE imo_number IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_vessels_mmsi
    ON public.vessels (mmsi)
    WHERE mmsi IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_vessels_name
    ON public.vessels (name);

CREATE INDEX IF NOT EXISTS idx_vessels_class
    ON public.vessels (vessel_class);

CREATE INDEX IF NOT EXISTS idx_vessels_ship_type
    ON public.vessels (ship_type);


-- ============================================================
-- PORT CONSTRAINTS
-- ============================================================

CREATE TABLE IF NOT EXISTS public.port_constraints (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    port_id uuid NOT NULL REFERENCES public.ports(id) ON DELETE CASCADE,

    max_loa_m double precision,
    max_beam_m double precision,
    max_draft_m double precision,
    cargo_handling_types jsonb,
    max_vessel_capacity_mt double precision,

    loading_available boolean,
    discharge_available boolean,

    source text,
    source_reference text,
    provenance text NOT NULL DEFAULT 'USER_PROVIDED',
    observed_at timestamptz,

    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT port_constraints_port_unique UNIQUE (port_id)
);

CREATE INDEX IF NOT EXISTS idx_port_constraints_port_id
    ON public.port_constraints (port_id);


-- ============================================================
-- FEASIBILITY RUNS
-- ============================================================

CREATE TABLE IF NOT EXISTS public.feasibility_runs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),

    cargo_requirement_id uuid NOT NULL
        REFERENCES public.cargo_requirements(id) ON DELETE CASCADE,
    vessel_id uuid NOT NULL
        REFERENCES public.vessels(id) ON DELETE CASCADE,
    origin_port_id uuid NOT NULL
        REFERENCES public.ports(id) ON DELETE RESTRICT,
    destination_port_id uuid NOT NULL
        REFERENCES public.ports(id) ON DELETE RESTRICT,

    result text NOT NULL,

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

    reasons jsonb NOT NULL DEFAULT '[]'::jsonb,
    checks jsonb NOT NULL DEFAULT '{}'::jsonb,

    provenance text NOT NULL DEFAULT 'DERIVED',
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_feasibility_runs_cargo
    ON public.feasibility_runs (cargo_requirement_id);

CREATE INDEX IF NOT EXISTS idx_feasibility_runs_vessel
    ON public.feasibility_runs (vessel_id);

CREATE INDEX IF NOT EXISTS idx_feasibility_runs_origin
    ON public.feasibility_runs (origin_port_id);

CREATE INDEX IF NOT EXISTS idx_feasibility_runs_destination
    ON public.feasibility_runs (destination_port_id);

CREATE INDEX IF NOT EXISTS idx_feasibility_runs_result
    ON public.feasibility_runs (result);


-- ============================================================
-- READ POLICIES
-- ============================================================
-- The API currently uses its privileged server-side Supabase client.
-- Public read policies also keep the schema compatible with future
-- read-only clients without granting public writes.

ALTER TABLE public.cargo_requirements ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.vessels ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.port_constraints ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.feasibility_runs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "public_read_cargo_requirements"
    ON public.cargo_requirements;
CREATE POLICY "public_read_cargo_requirements"
    ON public.cargo_requirements
    FOR SELECT
    TO anon, authenticated
    USING (true);

DROP POLICY IF EXISTS "public_read_vessels"
    ON public.vessels;
CREATE POLICY "public_read_vessels"
    ON public.vessels
    FOR SELECT
    TO anon, authenticated
    USING (true);

DROP POLICY IF EXISTS "public_read_port_constraints"
    ON public.port_constraints;
CREATE POLICY "public_read_port_constraints"
    ON public.port_constraints
    FOR SELECT
    TO anon, authenticated
    USING (true);

DROP POLICY IF EXISTS "public_read_feasibility_runs"
    ON public.feasibility_runs;
CREATE POLICY "public_read_feasibility_runs"
    ON public.feasibility_runs
    FOR SELECT
    TO anon, authenticated
    USING (true);


COMMENT ON TABLE public.cargo_requirements IS
    'Cargo requirements submitted for transportation/procurement decisions. Values retain explicit provenance.';

COMMENT ON TABLE public.vessels IS
    'Vessel master/intelligence records. AIS and other observations are source-backed and timestamped.';

COMMENT ON TABLE public.port_constraints IS
    'Physical/operational port constraints used by the feasibility gate.';

COMMENT ON TABLE public.feasibility_runs IS
    'Derived feasibility evaluations linking cargo, vessel and operational port constraints.';
