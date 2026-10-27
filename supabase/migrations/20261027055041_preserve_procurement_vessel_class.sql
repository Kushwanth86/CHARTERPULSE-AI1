-- CHARTERPULSE AI
-- Applied migration: 20261027055041_preserve_procurement_vessel_class.
-- Preserve the vessel class selected during procurement intake.
-- This migration is additive and safe for existing cargo requirements.

alter table public.cargo_requirements
    add column if not exists vessel_class text;

comment on column public.cargo_requirements.vessel_class is
    'Optional vessel class selected for the procurement; separate from cargo transport type.';
