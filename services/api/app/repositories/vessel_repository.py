from uuid import UUID

from services.api.app.repositories.supabase_client import get_supabase_admin_client


_SHARED_PROVENANCES = ["REAL", "PUBLIC_PROXY"]


class VesselRepository:
    def create(self, payload: dict, user_id: UUID) -> dict:
        client = get_supabase_admin_client()
        row = {**payload, "user_id": str(user_id), "provenance": "USER_PROVIDED"}
        response = client.table("vessels").insert(row).execute()
        if not response.data:
            raise RuntimeError("Failed to create vessel.")
        return response.data[0]

    def get(self, vessel_id: UUID, user_id: UUID) -> dict | None:
        client = get_supabase_admin_client()
        response = (
            client.table("vessels")
            .select("*")
            .eq("id", str(vessel_id))
            .or_(
                f"provenance.in.({','.join(_SHARED_PROVENANCES)}),user_id.eq.{user_id}"
            )
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None

    def list(self, user_id: UUID, limit: int = 100) -> list[dict]:
        client = get_supabase_admin_client()
        response = (
            client.table("vessels")
            .select("*")
            .or_(
                f"provenance.in.({','.join(_SHARED_PROVENANCES)}),user_id.eq.{user_id}"
            )
            .order("name")
            .limit(limit)
            .execute()
        )
        return response.data or []
