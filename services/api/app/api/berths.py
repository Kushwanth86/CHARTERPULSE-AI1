from fastapi import APIRouter

from services.api.app.services.berth_service import BerthService


router = APIRouter(
    prefix="/api/v1/berths",
    tags=["berths"],
)

berth_service = BerthService()


@router.get("")
def list_berths():
    berths = berth_service.list_berths()

    return {
        "count": len(berths),
        "data": berths,
    }
