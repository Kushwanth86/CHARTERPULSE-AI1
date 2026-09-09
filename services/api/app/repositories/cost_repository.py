from services.api.app.schemas.costs import TotalDeliveredCostRequest
from services.api.app.services.cost_service import CostService

service = CostService()


def calculate_cost(payload: TotalDeliveredCostRequest):
    return service.calculate(payload)
