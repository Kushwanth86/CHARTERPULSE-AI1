from fastapi import APIRouter

from services.api.app.repositories.supabase_client import get_supabase_client


router = APIRouter(
    prefix="/api/v1/ports",
    tags=["ports"],
)


@router.get("")
def list_ports():
    client = get_supabase_client()

    response = (
        client
        .table("ports")
        .select("*")
        .order("name")
        .execute()
    )

    return {
        "count": len(response.data or []),
        "data": response.data or [],
    }
