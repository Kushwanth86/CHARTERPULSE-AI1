from services.api.app.repositories.supabase_client import get_supabase_client


class HealthRepository:

    REQUIRED_TABLES = (
        "countries",
        "regions",
        "locations",
        "ports",
        "terminals",
        "berths",
        "cargo_requirements",
        "vessels",
        "port_constraints",
        "feasibility_runs",
    )

    def check_database(self) -> dict:
        client = get_supabase_client()
        checks = {}

        for table in self.REQUIRED_TABLES:
            try:
                response = (
                    client
                    .table(table)
                    .select("id")
                    .limit(1)
                    .execute()
                )
                checks[table] = {
                    "connected": True,
                    "rows_returned": len(response.data or []),
                }
            except Exception as exc:
                checks[table] = {
                    "connected": False,
                    "error": str(exc),
                }

        failed = [
            table
            for table, result in checks.items()
            if not result["connected"]
        ]

        return {
            "connected": not failed,
            "required_tables": len(self.REQUIRED_TABLES),
            "failed_tables": failed,
            "checks": checks,
        }
