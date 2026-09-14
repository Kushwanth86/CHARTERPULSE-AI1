from uuid import UUID

from services.api.app.repositories.supabase_client import get_supabase_admin_client


class ModelEvaluationRepository:
    def create(self, payload: dict) -> dict:
        client = get_supabase_admin_client()
        result = client.table("model_evaluations").insert(payload).execute()

        if not result.data:
            raise RuntimeError("Model evaluation could not be persisted.")

        return result.data[0]

    def list(
        self,
        *,
        model_name: str | None = None,
        model_version: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        client = get_supabase_admin_client()
        query = (
            client.table("model_evaluations")
            .select("*")
            .order("evaluated_at", desc=True)
            .limit(limit)
        )

        if model_name:
            query = query.eq("model_name", model_name)
        if model_version:
            query = query.eq("model_version", model_version)

        return query.execute().data or []

    def get_forecast(self, forecast_id: UUID) -> dict | None:
        client = get_supabase_admin_client()
        result = (
            client.table("freight_forecasts")
            .select("*")
            .eq("id", str(forecast_id))
            .limit(1)
            .execute()
        )

        return result.data[0] if result.data else None
