from uuid import UUID

from services.api.app.repositories.supabase_client import get_supabase_admin_client


_SHARED_PROVENANCES = ["REAL", "PUBLIC_PROXY"]


class VesselCargoCompatibilityRepository:
    def create(self, payload: dict, user_id: UUID) -> dict:
        client = get_supabase_admin_client()
        row = {**payload, "user_id": str(user_id), "provenance": "USER_PROVIDED"}
        # Insert, do not upsert on the global vessel/type key: an upsert could
        # overwrite a trusted provider rule or another user's rule.
        response = client.table("vessel_cargo_compatibility").insert(row).execute()
        if not response.data:
            raise RuntimeError("Failed to create vessel/cargo compatibility rule.")
        return response.data[0]

    def list_for_vessel(self, vessel_id: UUID, user_id: UUID) -> list[dict]:
        client = get_supabase_admin_client()
        response = (
            client.table("vessel_cargo_compatibility")
            .select("*")
            .eq("vessel_id", str(vessel_id))
            .or_(
                f"provenance.in.({','.join(_SHARED_PROVENANCES)}),user_id.eq.{user_id}"
            )
            .order("created_at", desc=True)
            .execute()
        )
        return response.data or []
