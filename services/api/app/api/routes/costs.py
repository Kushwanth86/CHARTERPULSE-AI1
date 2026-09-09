from fastapi import APIRouter

from services.api.app.schemas.costs import (
    TotalDeliveredCostRequest,
    TotalDeliveredCostResponse,
)
from services.api.app.services.cost_service import CostService


router = APIRouter(
    prefix="/api/v1/costs",
    tags=["costs"],
)

service = CostService()


@router.post(
    "/total-delivered",
    response_model=TotalDeliveredCostResponse,
)
def calculate_total_delivered_cost(
    payload: TotalDeliveredCostRequest,
):
    return service.calculate(payload)
