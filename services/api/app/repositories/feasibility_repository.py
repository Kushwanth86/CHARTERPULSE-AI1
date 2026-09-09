from services.api.app.repositories.supabase_client import (
    get_supabase_admin_client,
)


class FeasibilityRepository:

    def create(self, payload: dict) -> dict:
        client = get_supabase_admin_client()

        response = (
            client
            .table("feasibility_runs")
            .insert(payload)
            .execute()
        )

        if not response.data:
            raise RuntimeError(
                "Failed to store feasibility result."
            )

        return response.data[0]
