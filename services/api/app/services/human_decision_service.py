from fastapi import HTTPException

from services.api.app.schemas.human_decision import (
    HumanDecisionCreate,
    HumanDecisionResponse,
)
from services.api.app.repositories.supabase_client import get_supabase_admin_client


class HumanDecisionService:
    def create_decision(
        self,
        payload: HumanDecisionCreate,
    ) -> HumanDecisionResponse:
        supabase = get_supabase_admin_client()

        # Verify that the referenced AI decision exists.
        decision_result = (
            supabase.table("decision_runs")
            .select("id")
            .eq("id", payload.decision_run_id)
            .limit(1)
            .execute()
        )

        if not decision_result.data:
            raise HTTPException(
                status_code=404,
                detail=f"Decision run not found: {payload.decision_run_id}",
            )

        # MODIFY should carry actual modifications.
        if payload.action == "MODIFY" and not payload.modified_parameters:
            raise HTTPException(
                status_code=400,
                detail="modified_parameters is required when action is MODIFY",
            )

        row = {
            "decision_run_id": payload.decision_run_id,
            "action": payload.action,
            "modified_parameters": payload.modified_parameters,
            "reason": payload.reason,
            "actor_reference": payload.actor_reference,
            "provenance": "USER_PROVIDED",
        }

        result = (
            supabase.table("human_decisions")
            .insert(row)
            .execute()
        )

        if not result.data:
            raise HTTPException(
                status_code=500,
                detail="Human decision could not be persisted",
            )

        return HumanDecisionResponse(**result.data[0])


human_decision_service = HumanDecisionService()

