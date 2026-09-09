from fastapi import APIRouter, Query

from services.api.app.repositories.supabase_client import get_supabase_client


router = APIRouter(
    prefix="/api/v1/ports",
    tags=["ports"],
)


@router.get("")
def list_ports(
    country_code: str | None = Query(default=None, min_length=2, max_length=3),
    limit: int = Query(default=250, ge=1, le=1000),
):
    client = get_supabase_client()

    query = client.table("ports").select("*").order("name").limit(limit)

    if country_code:
        code = country_code.strip().upper()
        query = query.like("unlocode", f"{code}%")

    response = query.execute()

    return {
        "count": len(response.data or []),
        "data": response.data or [],
    }
