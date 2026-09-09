from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from services.api.app.schemas.forecasts import (
    FreightForecastRequest,
    FreightForecastResponse,
)
from services.api.app.services.forecast_service import (
    ForecastService,
)


router = APIRouter(
    prefix="/api/v1/forecasts",
    tags=["forecasts"],
)

service = ForecastService()


@router.post(
    "/freight",
    response_model=FreightForecastResponse,
)
def generate_freight_forecast(
    payload: FreightForecastRequest,
):

    try:
        return service.generate(payload)

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc


@router.get(
    "/freight",
    response_model=list[FreightForecastResponse],
)
def list_freight_forecasts(
    origin_location_id: UUID | None = None,
    destination_location_id: UUID | None = None,
    vessel_class: str | None = None,
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
    ),
):

    return service.list(
        origin_location_id=origin_location_id,
        destination_location_id=destination_location_id,
        vessel_class=vessel_class,
        limit=limit,
    )
