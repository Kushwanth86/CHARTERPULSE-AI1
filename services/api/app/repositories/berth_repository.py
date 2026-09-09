from services.api.app.repositories.supabase_client import get_supabase_client


class BerthRepository:

    def list_berths(self) -> list[dict]:
        client = get_supabase_client()

        response = (
            client
            .table("berths")
            .select("*")
            .order("name")
            .execute()
        )

        return response.data or []
