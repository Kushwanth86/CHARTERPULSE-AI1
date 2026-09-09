from fastapi import APIRouter

from services.api.app.services.country_service import CountryService


router = APIRouter(
    prefix="/api/v1/countries",
    tags=["countries"],
)

country_service = CountryService()


@router.get("")
def list_countries():
    countries = country_service.list_countries()

    return {
        "count": len(countries),
        "data": countries,
    }
