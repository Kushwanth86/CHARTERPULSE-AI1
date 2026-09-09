from fastapi import APIRouter

from services.api.app.services.location_service import LocationService


router = APIRouter(
    prefix="/api/v1/locations",
    tags=["locations"],
)

location_service = LocationService()


@router.get("")
def list_locations():
    locations = location_service.list_locations()

    return {
        "count": len(locations),
        "data": locations,
    }
