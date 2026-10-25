-- CHARTERPULSE AI
-- Migration 037: idempotent ingestion for source-backed freight observations.
--
-- These fields preserve the provider's stable row identity, data retrieval time,
-- database ingestion time, and a compact normalization audit trail. Existing
-- rows remain valid: fields that cannot be reconstructed historically are nullable.

ALTER TABLE public.market_observations
    ADD COLUMN IF NOT EXISTS source_record_id text,
    ADD COLUMN IF NOT EXISTS retrieved_at timestamptz,
    ADD COLUMN IF NOT EXISTS ingested_at timestamptz NOT NULL DEFAULT now(),
    ADD COLUMN IF NOT EXISTS metadata jsonb NOT NULL DEFAULT '{}'::jsonb;

-- A provider record ID must be stable and unique within one source. This
-- prevents a corrected or remapped route/date from silently duplicating a
-- previously imported source record. Legacy rows have NULL source_record_id
-- and are intentionally outside this index because their original identity
-- cannot be reconstructed reliably.
CREATE UNIQUE INDEX IF NOT EXISTS uq_market_observations_source_identity
    ON public.market_observations (source, source_record_id)
    WHERE source_record_id IS NOT NULL;

COMMENT ON COLUMN public.market_observations.source_record_id IS
    'Stable identifier of the original row/quote in the external source.';
COMMENT ON COLUMN public.market_observations.retrieved_at IS
    'Timestamp when the source observation was retrieved or exported.';
COMMENT ON COLUMN public.market_observations.ingested_at IS
    'Database-side ingestion timestamp; distinct from the market observation time.';
COMMENT ON COLUMN public.market_observations.metadata IS
    'Compact provenance and normalization audit metadata; never a substitute for source fields.';
