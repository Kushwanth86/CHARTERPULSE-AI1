from datetime import datetime
from uuid import UUID

from services.api.app.repositories.supabase_client import (
    get_supabase_admin_client,
)


class MarketRepository:

    def create(self, payload: dict) -> dict:
        client = get_supabase_admin_client()

        response = (
            client
            .table("market_observations")
            .insert(payload)
            .execute()
        )

        if not response.data:
            raise RuntimeError(
                "Failed to create market observation."
            )

        return response.data[0]

    def list(
        self,
        metric: str | None = None,
        origin_location_id: UUID | None = None,
        destination_location_id: UUID | None = None,
        vessel_class: str | None = None,
        limit: int = 500,
    ) -> list[dict]:

        client = get_supabase_admin_client()

        query = (
            client
            .table("market_observations")
            .select("*")
        )

        if metric:
            query = query.eq("metric", metric)

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
            .order("observed_at")
            .limit(limit)
            .execute()
        )

        return response.data or []
