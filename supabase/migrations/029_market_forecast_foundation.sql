-- CHARTERPULSE AI
-- Migration 029: Market observation and freight forecast foundation.
--
-- Stores source-backed market observations separately from derived forecasts.
-- No synthetic market values are inserted here.

CREATE TABLE IF NOT EXISTS public.market_observations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),

    market_type text NOT NULL,
    metric text NOT NULL,

    origin_location_id uuid REFERENCES public.locations(id) ON DELETE SET NULL,
    destination_location_id uuid REFERENCES public.locations(id) ON DELETE SET NULL,
    vessel_class text,

    value double precision NOT NULL CHECK (value > 0),
    unit text NOT NULL,
    currency text,

    observed_at timestamptz NOT NULL,

    source text NOT NULL,
    source_reference text,
    provenance text NOT NULL DEFAULT 'USER_PROVIDED'
        CHECK (provenance IN ('REAL','PUBLIC_PROXY','SIMULATED','USER_PROVIDED','DERIVED','FORECAST')),

    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_market_observations_metric_time
    ON public.market_observations (metric, observed_at);

CREATE INDEX IF NOT EXISTS idx_market_observations_route
    ON public.market_observations (origin_location_id, destination_location_id);

CREATE INDEX IF NOT EXISTS idx_market_observations_vessel_class
    ON public.market_observations (vessel_class);

CREATE INDEX IF NOT EXISTS idx_market_observations_provenance
    ON public.market_observations (provenance);


CREATE TABLE IF NOT EXISTS public.freight_forecasts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),

    origin_location_id uuid REFERENCES public.locations(id) ON DELETE SET NULL,
    destination_location_id uuid REFERENCES public.locations(id) ON DELETE SET NULL,
    vessel_class text,

    forecast_horizon_days integer NOT NULL CHECK (forecast_horizon_days >= 0),

    p10 double precision NOT NULL CHECK (p10 >= 0),
    p50 double precision NOT NULL CHECK (p50 >= 0),
    p90 double precision NOT NULL CHECK (p90 >= p50),
    baseline_value double precision NOT NULL CHECK (baseline_value >= 0),

    unit text NOT NULL,
    currency text NOT NULL,

    model_name text NOT NULL,
    model_version text NOT NULL,

    mae double precision,
    rmse double precision,
    smape double precision,
    interval_coverage double precision,
    confidence double precision NOT NULL CHECK (confidence >= 0 AND confidence <= 1),

    provenance text NOT NULL DEFAULT 'FORECAST'
        CHECK (provenance = 'FORECAST'),
    generated_at timestamptz NOT NULL DEFAULT now(),
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_freight_forecasts_generated_at
    ON public.freight_forecasts (generated_at DESC);

CREATE INDEX IF NOT EXISTS idx_freight_forecasts_route
    ON public.freight_forecasts (origin_location_id, destination_location_id);

CREATE INDEX IF NOT EXISTS idx_freight_forecasts_vessel_class
    ON public.freight_forecasts (vessel_class);


ALTER TABLE public.market_observations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.freight_forecasts ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "public_read_market_observations"
    ON public.market_observations;
CREATE POLICY "public_read_market_observations"
    ON public.market_observations
    FOR SELECT
    TO anon, authenticated
    USING (true);

DROP POLICY IF EXISTS "public_read_freight_forecasts"
    ON public.freight_forecasts;
CREATE POLICY "public_read_freight_forecasts"
    ON public.freight_forecasts
    FOR SELECT
    TO anon, authenticated
    USING (true);

GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT SELECT ON TABLE public.market_observations, public.freight_forecasts
    TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE
    ON TABLE public.market_observations, public.freight_forecasts
    TO service_role;

REVOKE INSERT, UPDATE, DELETE, TRUNCATE
    ON TABLE public.market_observations, public.freight_forecasts
    FROM anon, authenticated;

COMMENT ON TABLE public.market_observations IS
    'Source-backed market observations used as inputs to forecasting and decision intelligence.';

COMMENT ON TABLE public.freight_forecasts IS
    'Derived probabilistic freight forecasts with model metadata and uncertainty intervals.';
