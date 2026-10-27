from uuid import UUID

from services.api.app.repositories.supabase_client import (
    get_supabase_admin_client,
)


class FeasibilityRepository:

    def create(self, payload: dict, user_id: UUID) -> dict:
        client = get_supabase_admin_client()
        row = {**payload, "user_id": str(user_id)}

        response = (
            client
            .table("feasibility_runs")
            .insert(row)
            .execute()
        )

        if not response.data:
            raise RuntimeError(
                "Failed to store feasibility result."
            )

        return response.data[0]
