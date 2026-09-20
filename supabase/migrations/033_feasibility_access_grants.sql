-- CHARTERPULSE AI
-- Migration 033: feasibility and vessel/cargo access grants
--
-- Explicit privileges complement the RLS policies created by
-- migrations 029 and 032.

GRANT USAGE ON SCHEMA public TO anon, authenticated;

-- Vessel intelligence
GRANT SELECT ON TABLE public.vessels
    TO anon, authenticated;

GRANT SELECT, INSERT, UPDATE, DELETE
    ON TABLE public.vessels
    TO service_role;

REVOKE INSERT, UPDATE, DELETE, TRUNCATE
    ON TABLE public.vessels
    FROM anon, authenticated;


-- Port physical constraints
GRANT SELECT ON TABLE public.port_constraints
    TO anon, authenticated;

GRANT SELECT, INSERT, UPDATE, DELETE
    ON TABLE public.port_constraints
    TO service_role;

REVOKE INSERT, UPDATE, DELETE, TRUNCATE
    ON TABLE public.port_constraints
    FROM anon, authenticated;


-- Feasibility runs
GRANT SELECT ON TABLE public.feasibility_runs
    TO anon, authenticated;

GRANT SELECT, INSERT, UPDATE, DELETE
    ON TABLE public.feasibility_runs
    TO service_role;

REVOKE INSERT, UPDATE, DELETE, TRUNCATE
    ON TABLE public.feasibility_runs
    FROM anon, authenticated;


-- Explicit vessel/cargo compatibility
GRANT SELECT ON TABLE public.vessel_cargo_compatibility
    TO anon, authenticated;

GRANT SELECT, INSERT, UPDATE, DELETE
    ON TABLE public.vessel_cargo_compatibility
    TO service_role;

REVOKE INSERT, UPDATE, DELETE, TRUNCATE
    ON TABLE public.vessel_cargo_compatibility
    FROM anon, authenticated;


COMMENT ON TABLE public.feasibility_runs IS
    'Derived physical feasibility evaluations. Results must be explainable through checks and reasons.';
