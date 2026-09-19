from uuid import UUID

from services.api.app.repositories.supabase_client import (
    get_supabase_client,
    get_supabase_admin_client,
)


class VesselCargoCompatibilityRepository:

    def create(self, payload: dict) -> dict:
        payload = dict(payload)
        if isinstance(payload.get("vessel_id"), UUID):
            payload["vessel_id"] = str(payload["vessel_id"])

        client = get_supabase_admin_client()
        response = (
            client
            .table("vessel_cargo_compatibility")
            .upsert(payload, on_conflict="vessel_id,cargo_type,material")
            .execute()
        )

        if not response.data:
            raise RuntimeError("Failed to create vessel/cargo compatibility rule.")

        return response.data[0]

    def list_for_vessel(self, vessel_id: UUID) -> list[dict]:
        client = get_supabase_client()
        response = (
            client
            .table("vessel_cargo_compatibility")
            .select("*")
            .eq("vessel_id", str(vessel_id))
            .order("created_at", desc=True)
            .execute()
        )
        return response.data or []
