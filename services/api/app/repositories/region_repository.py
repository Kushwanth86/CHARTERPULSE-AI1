from services.api.app.repositories.supabase_client import get_supabase_client


class RegionRepository:

    def list_regions(self) -> list[dict]:
        client = get_supabase_client()

        response = (
            client
            .table("regions")
            .select("*")
            .order("name")
            .execute()
        )

        return response.data or []
