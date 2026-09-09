from fastapi import APIRouter

from services.api.app.api.routes import (
    cargo,
    charter_scenarios,
    costs,
    decision,
    feasibility,
    forecasts,
    human_decision,
    market,
    port_constraints,
    risk,
    vessels,
)

router = APIRouter()

router.include_router(cargo.router)
router.include_router(market.router)
router.include_router(forecasts.router)
router.include_router(vessels.router)
router.include_router(feasibility.router)
router.include_router(port_constraints.router)
router.include_router(costs.router)
router.include_router(charter_scenarios.router)
router.include_router(risk.router)
router.include_router(decision.router)
router.include_router(human_decision.router)
