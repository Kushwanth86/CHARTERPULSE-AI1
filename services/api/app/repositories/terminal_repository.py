from services.api.app.repositories.supabase_client import get_supabase_client


class TerminalRepository:

    def list_terminals(self) -> list[dict]:
        client = get_supabase_client()

        response = (
            client
            .table("terminals")
            .select("*")
            .order("name")
            .execute()
        )

        return response.data or []
