-- CHARTERPULSE AI
-- Migration 030: Actual decision outcomes and human feedback.
--
-- Closes the learning loop:
-- prediction -> recommendation -> human decision -> actual outcome -> feedback.
-- No synthetic outcomes are inserted by this migration.

CREATE TABLE IF NOT EXISTS public.decision_outcomes (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),

    decision_run_id uuid NOT NULL
        REFERENCES public.decision_runs(id) ON DELETE CASCADE,
    human_decision_id uuid
        REFERENCES public.human_decisions(id) ON DELETE SET NULL,

    actual_freight_rate_per_mt double precision
        CHECK (actual_freight_rate_per_mt >= 0),
    actual_total_cost double precision
        CHECK (actual_total_cost >= 0),
    currency text NOT NULL DEFAULT 'USD',

    actual_cost_components jsonb NOT NULL DEFAULT '{}'::jsonb,

    actual_delivery_at timestamptz,
    delivery_delay_days double precision
        CHECK (delivery_delay_days >= 0),

    source text,
    source_reference text,
    provenance text NOT NULL DEFAULT 'USER_PROVIDED'
        CHECK (provenance IN ('REAL','USER_PROVIDED','DERIVED')),

    notes text,
    recorded_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_decision_outcomes_run
    ON public.decision_outcomes(decision_run_id);

CREATE INDEX IF NOT EXISTS idx_decision_outcomes_recorded
    ON public.decision_outcomes(recorded_at DESC);


CREATE TABLE IF NOT EXISTS public.decision_feedback (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),

    decision_run_id uuid NOT NULL
        REFERENCES public.decision_runs(id) ON DELETE CASCADE,
    outcome_id uuid
        REFERENCES public.decision_outcomes(id) ON DELETE SET NULL,

    rating integer CHECK (rating >= 1 AND rating <= 5),
    recommendation_followed boolean,
    correctness text NOT NULL DEFAULT 'NOT_EVALUATED'
        CHECK (correctness IN ('CORRECT','PARTIALLY_CORRECT','INCORRECT','NOT_EVALUATED')),

    comment text,
    actor_reference text,
    provenance text NOT NULL DEFAULT 'USER_PROVIDED'
        CHECK (provenance IN ('USER_PROVIDED','DERIVED')),

    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_decision_feedback_run
    ON public.decision_feedback(decision_run_id);

CREATE INDEX IF NOT EXISTS idx_decision_feedback_outcome
    ON public.decision_feedback(outcome_id);


ALTER TABLE public.decision_outcomes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.decision_feedback ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "public_read_decision_outcomes"
    ON public.decision_outcomes;
CREATE POLICY "public_read_decision_outcomes"
    ON public.decision_outcomes
    FOR SELECT
    TO anon, authenticated
    USING (true);

DROP POLICY IF EXISTS "public_read_decision_feedback"
    ON public.decision_feedback;
CREATE POLICY "public_read_decision_feedback"
    ON public.decision_feedback
    FOR SELECT
    TO anon, authenticated
    USING (true);

GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT SELECT ON TABLE public.decision_outcomes, public.decision_feedback
    TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE
    ON TABLE public.decision_outcomes, public.decision_feedback
    TO service_role;

REVOKE INSERT, UPDATE, DELETE, TRUNCATE
    ON TABLE public.decision_outcomes, public.decision_feedback
    FROM anon, authenticated;

COMMENT ON TABLE public.decision_outcomes IS
    'Observed outcomes of transportation decisions used for model and decision evaluation.';

COMMENT ON TABLE public.decision_feedback IS
    'Human feedback linking decision quality to observed outcomes.';
