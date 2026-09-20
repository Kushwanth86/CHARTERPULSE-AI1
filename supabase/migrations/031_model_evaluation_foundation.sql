-- CHARTERPULSE AI
-- Migration 031: Forecast model evaluation foundation.
--
-- Stores evaluations only when an observed actual value is available.
-- No synthetic performance values are inserted here.

CREATE TABLE IF NOT EXISTS public.model_evaluations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),

    forecast_id uuid NOT NULL
        REFERENCES public.freight_forecasts(id) ON DELETE CASCADE,

    evaluation_type text NOT NULL DEFAULT 'FORECAST_ACCURACY'
        CHECK (evaluation_type = 'FORECAST_ACCURACY'),

    model_name text NOT NULL,
    model_version text NOT NULL,

    actual_value double precision NOT NULL CHECK (actual_value > 0),
    actual_unit text NOT NULL,
    actual_currency text,
    actual_observed_at timestamptz NOT NULL,

    predicted_p10 double precision NOT NULL CHECK (predicted_p10 >= 0),
    predicted_p50 double precision NOT NULL CHECK (predicted_p50 >= 0),
    predicted_p90 double precision NOT NULL CHECK (predicted_p90 >= predicted_p50),

    signed_error double precision NOT NULL,
    absolute_error double precision NOT NULL CHECK (absolute_error >= 0),
    squared_error double precision NOT NULL CHECK (squared_error >= 0),
    smape double precision NOT NULL CHECK (smape >= 0),
    interval_covered boolean NOT NULL,

    actual_provenance text NOT NULL DEFAULT 'USER_PROVIDED'
        CHECK (actual_provenance IN ('REAL','USER_PROVIDED','DERIVED')),
    source text,
    source_reference text,
    notes text,

    evaluated_at timestamptz NOT NULL DEFAULT now(),
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_model_evaluations_forecast
    ON public.model_evaluations (forecast_id);

CREATE INDEX IF NOT EXISTS idx_model_evaluations_model_version
    ON public.model_evaluations (model_name, model_version, evaluated_at DESC);

CREATE INDEX IF NOT EXISTS idx_model_evaluations_actual_time
    ON public.model_evaluations (actual_observed_at DESC);

ALTER TABLE public.model_evaluations ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "public_read_model_evaluations"
    ON public.model_evaluations;
CREATE POLICY "public_read_model_evaluations"
    ON public.model_evaluations
    FOR SELECT
    TO anon, authenticated
    USING (true);

GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT SELECT ON TABLE public.model_evaluations TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE
    ON TABLE public.model_evaluations TO service_role;

REVOKE INSERT, UPDATE, DELETE, TRUNCATE
    ON TABLE public.model_evaluations
    FROM anon, authenticated;

COMMENT ON TABLE public.model_evaluations IS
    'Observed forecast evaluations used to measure model accuracy and prediction-interval coverage.';
