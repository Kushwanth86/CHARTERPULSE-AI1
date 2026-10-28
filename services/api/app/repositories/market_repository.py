from uuid import UUID

from services.api.app.repositories.supabase_client import get_supabase_admin_client


class MarketRepository:
    def create(self, payload: dict, user_id: UUID) -> dict:
        client = get_supabase_admin_client()
        row = {**payload, "user_id": str(user_id)}
        response = client.table("market_observations").insert(row).execute()
        if not response.data:
            raise RuntimeError("Failed to create market observation.")
        return response.data[0]

    def list(
        self,
        metric: str | list[str] | None = None,
        origin_location_id: UUID | None = None,
        destination_location_id: UUID | None = None,
        vessel_class: str | None = None,
        limit: int = 500,
        user_id: UUID | None = None,
    ) -> list[dict]:
        client = get_supabase_admin_client()
        query = client.table("market_observations").select("*")

        if isinstance(metric, list):
            normalized_metrics = sorted(
                {str(value).strip() for value in metric if str(value).strip()}
            )
            if not normalized_metrics:
                return []
            query = query.in_("metric", normalized_metrics)
        elif metric:
            query = query.eq("metric", metric)

        if origin_location_id:
            query = query.eq("origin_location_id", str(origin_location_id))
        if destination_location_id:
            query = query.eq("destination_location_id", str(destination_location_id))
        if vessel_class:
            query = query.ilike("vessel_class", vessel_class.strip())

        # Trusted provider rows can be shared across users; caller-submitted
        # rows are visible only to their verified owner. Never return legacy
        # USER_PROVIDED rows with no owner.
        if user_id is None:
            query = query.in_("provenance", ["REAL", "PUBLIC_PROXY"])
        else:
            query = query.or_(
                f"provenance.in.(REAL,PUBLIC_PROXY),and(provenance.eq.USER_PROVIDED,user_id.eq.{user_id})"
            )

        response = (
            query.order("observed_at", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data or []
