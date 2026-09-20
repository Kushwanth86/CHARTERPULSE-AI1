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
    ) -> DecisionOutcomeResponse:
        client = get_supabase_admin_client()

        row = payload.model_dump(mode="json")
        result = client.table("decision_outcomes").insert(row).execute()

        if not result.data:
            raise RuntimeError("Decision outcome could not be persisted.")

        return DecisionOutcomeResponse.model_validate(result.data[0])


class FeedbackService:
    def create_feedback(
        self,
        payload: DecisionFeedbackCreate,
    ) -> DecisionFeedbackResponse:
        client = get_supabase_admin_client()

        row = payload.model_dump(mode="json")
        result = client.table("decision_feedback").insert(row).execute()

        if not result.data:
            raise RuntimeError("Decision feedback could not be persisted.")

        return DecisionFeedbackResponse.model_validate(result.data[0])


outcome_service = OutcomeService()
feedback_service = FeedbackService()
