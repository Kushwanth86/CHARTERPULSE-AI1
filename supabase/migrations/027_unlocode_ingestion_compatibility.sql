-- CHARTERPULSE AI
-- UN/LOCODE ingestion compatibility correction
-- Depends on 026_unlocode_foundation.sql

-- The parser preserves the source relationship semantics
-- "SAME_LOCODE_SOURCE_HISTORY". Allow that value explicitly.

alter table public.unlocode_source_relationships
    drop constraint if exists unlocode_source_relationships_relationship_check;

alter table public.unlocode_source_relationships
    add constraint unlocode_source_relationships_relationship_check
    check (
        relationship in (
            'CANONICAL',
            'DUPLICATE',
            'HISTORY',
            'SAME_LOCODE_SOURCE_HISTORY'
        )
    );


-- Replace the partial unique index with a normal UNIQUE constraint.
-- PostgreSQL UNIQUE permits multiple NULLs, so locations without
-- a UN/LOCODE remain valid while non-null LOCODEs are unique.

drop index if exists public.uq_locations_unlocode;

alter table public.locations
    drop constraint if exists locations_unlocode_unique;

alter table public.locations
    add constraint locations_unlocode_unique
    unique (unlocode);
