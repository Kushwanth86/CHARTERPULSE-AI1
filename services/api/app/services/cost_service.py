from services.api.app.schemas.costs import (
    TotalDeliveredCostRequest,
    TotalDeliveredCostResponse,
)
from services.api.app.intelligence.total_delivered_cost import (
    calculate_total_delivered_cost,
)


class CostService:
    def calculate(self, payload: TotalDeliveredCostRequest) -> TotalDeliveredCostResponse:
        return calculate_total_delivered_cost(payload)
