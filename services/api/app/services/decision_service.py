from services.api.app.decision.decision_engine import (
    DecisionRequest,
    DecisionResponse,
    evaluate_decision,
)
from services.api.app.repositories.supabase_client import (
    get_supabase_admin_client,
)


class DecisionService:

    def evaluate(
        self,
        payload: DecisionRequest,
    ) -> DecisionResponse:
        # Keep the existing decision mathematics unchanged.
        decision = evaluate_decision(payload)

        supabase = get_supabase_admin_client()

        # Persist the AI decision so that a human decision can reference it.
        row = {
            "recommendation": decision.recommendation,
            "recommendation_score": None,
            "expected_total_cost": decision.now_expected_freight_cost,
            "expected_cost_unit": decision.currency,
            "expected_cost_currency": decision.currency,
            "risk_score": decision.risk_score,
            "confidence": None,
            "rationale": " ".join(decision.rationale),
            "forecast_snapshot": {
                "forecast_id": str(decision.forecast_id),
                "model_name": decision.model_name,
                "p10": decision.forecast_p10,
                "p50": decision.forecast_p50,
                "p90": decision.forecast_p90,
                "provenance": decision.provenance,
            },
            "feasibility_snapshot": {},
            "cost_snapshot": {
                "cargo_quantity_mt": decision.cargo_quantity_mt,
                "currency": decision.currency,
                "now_expected_freight_cost": (
                    decision.now_expected_freight_cost
                ),
                "now_p90_freight_cost": (
                    decision.now_p90_freight_cost
                ),
                "wait_conservative_rate": (
                    decision.wait_conservative_rate
                ),
                "wait_conservative_cost": (
                    decision.wait_conservative_cost
                ),
                "wait_cost_difference": (
                    decision.wait_cost_difference
                ),
                "wait_cost_difference_per_mt": (
                    decision.wait_cost_difference_per_mt
                ),
            },
            "risk_snapshot": {
                "probability_now_exceeds_baseline": (
                    decision.probability_now_exceeds_baseline
                ),
                "risk_score": decision.risk_score,
            },
            "optimization_snapshot": {},
            "provenance": decision.provenance,
        }

        # Attach cargo requirement when supplied by the request.
        if getattr(payload, "cargo_requirement_id", None):
            row["cargo_requirement_id"] = str(
                payload.cargo_requirement_id
            )

        result = (
            supabase
            .table("decision_runs")
            .insert(row)
            .execute()
        )

        if not result.data:
            raise RuntimeError(
                "Decision could not be persisted to decision_runs."
            )

        decision_run_id = str(result.data[0]["id"])

        # Return the same decision plus its persisted run identifier.
        return decision.model_copy(
            update={
                "decision_run_id": decision_run_id,
            }
        )
