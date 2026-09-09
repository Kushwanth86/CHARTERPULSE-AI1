from services.api.app.repositories.supabase_client import get_supabase_client


class CountryRepository:

    def list_countries(self) -> list[dict]:
        client = get_supabase_client()

        response = (
            client
            .table("countries")
            .select("*")
            .order("name")
            .execute()
        )

        return response.data or []
