-- ============================================================
-- CHARTERPULSE AI
-- MIGRATION 030
-- UNECE UN/LOCODE -> PORT INTELLIGENCE
-- ============================================================
--
-- Promote ONLY locations whose UN/LOCODE function begins with
-- "1", which represents a port function.
--
-- Do NOT promote rail, road, airport, postal, or multimodal-only
-- locations into the operational ports table.
--
-- UN/LOCODE does not provide operational draft, LOA, beam,
-- capacity, storage, connectivity, or berth constraints.
-- Those fields remain NULL until source-backed data is loaded.
-- ============================================================

INSERT INTO public.ports (
    location_id,
    name,
    latitude,
    longitude,
    unlocode,
    source,
    source_url,
    observed_at,
    updated_at
)
SELECT
    l.id,
    l.name,
    l.latitude,
    l.longitude,
    l.unlocode,
    'UNECE UN/LOCODE 2025-1',
    'https://unece.org/trade/cefact/UNLOCODE-Download',
    NULL,
    now()
FROM public.locations l
WHERE l.unlocode IS NOT NULL
  AND l.unlocode <> ''
  AND l.function IS NOT NULL
  AND substring(l.function from 1 for 1) = '1'
  AND NOT EXISTS (
      SELECT 1
      FROM public.ports p
      WHERE p.unlocode = l.unlocode
  );

-- Synchronize fields directly supported by the canonical
-- UN/LOCODE location record.
UPDATE public.ports p
SET
    name = l.name,
    latitude = l.latitude,
    longitude = l.longitude,
    source = 'UNECE UN/LOCODE 2025-1',
    source_url = 'https://unece.org/trade/cefact/UNLOCODE-Download',
    updated_at = now()
FROM public.locations l
WHERE p.location_id = l.id
  AND p.unlocode = l.unlocode
  AND l.function IS NOT NULL
  AND substring(l.function from 1 for 1) = '1';

COMMENT ON COLUMN public.ports.max_draft_m IS
    'Source-backed operational constraint. NULL when unavailable.';

COMMENT ON COLUMN public.ports.max_loa_m IS
    'Source-backed operational constraint. NULL when unavailable.';

COMMENT ON COLUMN public.ports.max_beam_m IS
    'Source-backed operational constraint. NULL when unavailable.';

COMMENT ON COLUMN public.ports.annual_capacity_tonnes IS
    'Source-backed port capacity. NULL when unavailable.';

COMMENT ON COLUMN public.ports.storage_capacity_tonnes IS
    'Source-backed storage capacity. NULL when unavailable.';

COMMENT ON COLUMN public.ports.rail_connected IS
    'Source-backed connectivity attribute. NULL when unavailable.';

COMMENT ON COLUMN public.ports.road_connected IS
    'Source-backed connectivity attribute. NULL when unavailable.';

COMMENT ON COLUMN public.ports.pipeline_connected IS
    'Source-backed connectivity attribute. NULL when unavailable.';
