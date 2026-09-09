from fastapi import APIRouter

from services.api.app.services.region_service import RegionService


router = APIRouter(
    prefix="/api/v1/regions",
    tags=["regions"],
)

region_service = RegionService()


@router.get("")
def list_regions():
    regions = region_service.list_regions()

    return {
        "count": len(regions),
        "data": regions,
    }
