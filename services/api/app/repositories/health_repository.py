from services.api.app.repositories.supabase_client import get_supabase_client


class HealthRepository:

    def check_database(self) -> dict:
        try:
            client = get_supabase_client()
            response = (
                client
                .table("countries")
                .select("id")
                .limit(1)
                .execute()
            )

            return {
                "connected": True,
                "table": "countries",
                "rows_returned": len(response.data or []),
            }

        except Exception as exc:
            return {
                "connected": False,
                "table": "countries",
                "error": str(exc),
            }
