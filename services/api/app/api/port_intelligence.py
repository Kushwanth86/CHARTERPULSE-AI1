from fastapi import APIRouter, Query

from services.api.app.services.port_intelligence_service import (
    PortIntelligenceService,
)


router = APIRouter(
    prefix="/api/v1/port-intelligence",
    tags=["port-intelligence"],
)


def get_service() -> PortIntelligenceService:
    """Create the Supabase-backed service only when an API request needs it."""
    return PortIntelligenceService()


@router.get("/summary")
def port_intelligence_summary():
    return get_service().summary()


@router.get("/search")
def search_ports(
    q: str | None = Query(default=None, min_length=1),
    country_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    data = get_service().search_ports(
        query=q,
        country_id=country_id,
        limit=limit,
        offset=offset,
    )

    return {
        "count": len(data),
        "limit": limit,
        "offset": offset,
        "data": data,
    }
