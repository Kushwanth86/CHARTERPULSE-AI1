-- CHARTERPULSE AI
-- Migration 032: explicit vessel/cargo compatibility rules.
--
-- Compatibility is source-backed data. The feasibility engine does not infer
-- compatibility from vessel class names or cargo material names.

CREATE TABLE IF NOT EXISTS public.vessel_cargo_compatibility (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),

    vessel_id uuid NOT NULL
        REFERENCES public.vessels(id) ON DELETE CASCADE,

    cargo_type text,
    material text,
    allowed boolean NOT NULL DEFAULT true,

    source text,
    source_reference text,
    provenance text NOT NULL DEFAULT 'USER_PROVIDED'
        CHECK (provenance IN (
            'REAL',
            'PUBLIC_PROXY',
            'SIMULATED',
            'USER_PROVIDED',
            'DERIVED',
            'FORECAST'
        )),

    observed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT vessel_cargo_compatibility_target_check
        CHECK (cargo_type IS NOT NULL OR material IS NOT NULL),

    CONSTRAINT vessel_cargo_compatibility_unique_rule
        UNIQUE (vessel_id, cargo_type, material)
);

CREATE INDEX IF NOT EXISTS idx_vessel_cargo_compatibility_vessel
    ON public.vessel_cargo_compatibility (vessel_id);

CREATE INDEX IF NOT EXISTS idx_vessel_cargo_compatibility_cargo_type
    ON public.vessel_cargo_compatibility (cargo_type);

CREATE INDEX IF NOT EXISTS idx_vessel_cargo_compatibility_material
    ON public.vessel_cargo_compatibility (material);

ALTER TABLE public.vessel_cargo_compatibility ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS vessel_cargo_compatibility_public_read
    ON public.vessel_cargo_compatibility;

CREATE POLICY vessel_cargo_compatibility_public_read
    ON public.vessel_cargo_compatibility
    FOR SELECT
    TO anon, authenticated
    USING (true);

COMMENT ON TABLE public.vessel_cargo_compatibility IS
    'Explicit source-backed vessel/cargo compatibility rules. Absence of a matching rule means compatibility is unknown, not assumed.';
