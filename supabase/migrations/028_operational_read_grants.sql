-- CHARTERPULSE AI
-- Migration 028: Make operational read privileges explicit.
--
-- RLS policies in 025-027 define row-level access, but table privileges are
-- kept explicit here so PostgREST/API reads do not depend on project defaults.
-- No market, freight, vessel or cargo values are inserted by this migration.

GRANT USAGE ON SCHEMA public TO anon, authenticated;

GRANT SELECT ON TABLE
    public.countries,
    public.regions,
    public.locations,
    public.ports,
    public.terminals,
    public.berths,
    public.unlocode_source_records,
    public.unlocode_locations,
    public.unlocode_source_relationships,
    public.cargo_requirements,
    public.vessels,
    public.port_constraints,
    public.feasibility_runs
TO anon, authenticated;

-- Keep write operations server-side through the privileged Supabase client.
REVOKE INSERT, UPDATE, DELETE, TRUNCATE
ON TABLE
    public.cargo_requirements,
    public.vessels,
    public.port_constraints,
    public.feasibility_runs
FROM anon, authenticated;
