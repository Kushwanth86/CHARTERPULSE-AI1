from uuid import UUID

from services.api.app.repositories.supabase_client import (
    get_supabase_admin_client,
)


class VesselRepository:

    def create(self, payload: dict) -> dict:
        client = get_supabase_admin_client()

        response = (
            client
            .table("vessels")
            .insert(payload)
            .execute()
        )

        if not response.data:
            raise RuntimeError("Failed to create vessel.")

        return response.data[0]

    def get(self, vessel_id: UUID) -> dict | None:
        client = get_supabase_admin_client()

        response = (
            client
            .table("vessels")
            .select("*")
            .eq("id", str(vessel_id))
            .limit(1)
            .execute()
        )

        return response.data[0] if response.data else None

    def list(self, limit: int = 100) -> list[dict]:
        client = get_supabase_admin_client()

        response = (
            client
            .table("vessels")
            .select("*")
            .order("name")
            .limit(limit)
            .execute()
        )

        return response.data or []
