from uuid import UUID

from services.api.app.repositories.supabase_client import (
    get_supabase_admin_client,
)


class ForecastRepository:

    def create(self, payload: dict) -> dict:
        client = get_supabase_admin_client()

        response = (
            client
            .table("freight_forecasts")
            .insert(payload)
            .execute()
        )

        if not response.data:
            raise RuntimeError(
                "Failed to store freight forecast."
            )

        return response.data[0]

    def list(
        self,
        origin_location_id: UUID | None = None,
        destination_location_id: UUID | None = None,
        vessel_class: str | None = None,
        limit: int = 100,
    ) -> list[dict]:

        client = get_supabase_admin_client()

        query = (
            client
            .table("freight_forecasts")
            .select("*")
        )

        if origin_location_id:
            query = query.eq(
                "origin_location_id",
                str(origin_location_id),
            )

        if destination_location_id:
            query = query.eq(
                "destination_location_id",
                str(destination_location_id),
            )

        if vessel_class:
            query = query.eq(
                "vessel_class",
                vessel_class,
            )

        response = (
            query
            .order("generated_at", desc=True)
            .limit(limit)
            .execute()
        )

        return response.data or []
