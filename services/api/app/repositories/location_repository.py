from services.api.app.repositories.supabase_client import get_supabase_client


class LocationRepository:

    def list_locations(self) -> list[dict]:
        client = get_supabase_client()

        response = (
            client
            .table("locations")
            .select("*")
            .order("name")
            .execute()
        )

        return response.data or []
