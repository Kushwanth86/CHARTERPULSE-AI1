from uuid import UUID

from services.api.app.repositories.supabase_client import get_supabase_admin_client


class CargoRepository:
    def create(self, payload: dict, user_id: UUID) -> dict:
        client = get_supabase_admin_client()
        row = {**payload, "user_id": str(user_id)}
        response = client.table("cargo_requirements").insert(row).execute()
        if not response.data:
            raise RuntimeError("Failed to create cargo requirement.")
        return response.data[0]

    def get(self, cargo_id: UUID, user_id: UUID) -> dict | None:
        client = get_supabase_admin_client()
        response = (
            client.table("cargo_requirements")
            .select("*")
            .eq("id", str(cargo_id))
            .eq("user_id", str(user_id))
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None

    def list(self, user_id: UUID, limit: int = 100) -> list[dict]:
        client = get_supabase_admin_client()
        response = (
            client.table("cargo_requirements")
            .select("*")
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data or []
