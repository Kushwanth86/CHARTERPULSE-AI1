from uuid import UUID

from fastapi import HTTPException

from services.api.app.repositories.supabase_client import get_supabase_admin_client
from services.api.app.schemas.outcomes import (
    DecisionFeedbackCreate,
    DecisionFeedbackResponse,
    DecisionOutcomeCreate,
    DecisionOutcomeResponse,
)


class OutcomeService:
    def create_outcome(
        self,
        payload: DecisionOutcomeCreate,
        user_id: UUID,
    ) -> DecisionOutcomeResponse:
        client = get_supabase_admin_client()

        decision = (
            client.table("decision_runs").select("id")
            .eq("id", str(payload.decision_run_id))
            .eq("user_id", str(user_id)).limit(1).execute()
        )
        if not decision.data:
            raise HTTPException(status_code=404, detail="Decision run not found.")
        if payload.human_decision_id is not None:
            human_decision = (
                client.table("human_decisions").select("id")
                .eq("id", str(payload.human_decision_id))
                .eq("user_id", str(user_id)).limit(1).execute()
            )
            if not human_decision.data:
                raise HTTPException(status_code=404, detail="Human decision not found.")
        row = payload.model_dump(mode="json")
        row["user_id"] = str(user_id)
        result = client.table("decision_outcomes").insert(row).execute()

        if not result.data:
            raise RuntimeError("Decision outcome could not be persisted.")

        return DecisionOutcomeResponse.model_validate(result.data[0])


class FeedbackService:
    def create_feedback(
        self,
        payload: DecisionFeedbackCreate,
        user_id: UUID,
    ) -> DecisionFeedbackResponse:
        client = get_supabase_admin_client()

        decision = (
            client.table("decision_runs").select("id")
            .eq("id", str(payload.decision_run_id))
            .eq("user_id", str(user_id)).limit(1).execute()
        )
        if not decision.data:
            raise HTTPException(status_code=404, detail="Decision run not found.")
        if payload.outcome_id is not None:
            outcome = (
                client.table("decision_outcomes").select("id")
                .eq("id", str(payload.outcome_id))
                .eq("user_id", str(user_id)).limit(1).execute()
            )
            if not outcome.data:
                raise HTTPException(status_code=404, detail="Decision outcome not found.")
        row = payload.model_dump(mode="json")
        row["user_id"] = str(user_id)
        row["actor_reference"] = str(user_id)
        result = client.table("decision_feedback").insert(row).execute()

        if not result.data:
            raise RuntimeError("Decision feedback could not be persisted.")

        return DecisionFeedbackResponse.model_validate(result.data[0])


outcome_service = OutcomeService()
feedback_service = FeedbackService()
