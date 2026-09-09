from uuid import UUID

from fastapi import APIRouter, Query, status

from services.api.app.schemas.market import (
    MarketObservationCreate,
    MarketObservationResponse,
)
from services.api.app.services.market_service import (
    MarketService,
)


router = APIRouter(
    prefix="/api/v1/market",
    tags=["market"],
)

service = MarketService()


@router.post(
    "/observations",
    response_model=MarketObservationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_observation(
    payload: MarketObservationCreate,
):
    return service.create(payload)


@router.get(
    "/observations",
    response_model=list[MarketObservationResponse],
)
def list_observations(
    metric: str | None = None,
    origin_location_id: UUID | None = None,
    destination_location_id: UUID | None = None,
    vessel_class: str | None = None,
    limit: int = Query(
        default=500,
        ge=1,
        le=1000,
    ),
):
    return service.list(
        metric=metric,
        origin_location_id=origin_location_id,
        destination_location_id=destination_location_id,
        vessel_class=vessel_class,
        limit=limit,
    )
