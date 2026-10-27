from fastapi import APIRouter, Depends

from services.api.app.api.routes import (
    cargo,
    charter_scenarios,
    costs,
    decision,
    feasibility,
    forecasts,
    freightos,
    human_decision,
    market,
    model_evaluation,
    outcomes,
    port_constraints,
    risk,
    vessel_cargo_compatibility,
    vessels,
)
from services.api.app.security.current_user import get_current_user_id
from services.api.app.security.rate_limit import enforce_user_rate_limit


# All /api/v1 routes require a valid Supabase Auth session. Public, read-only
# reference-data endpoints remain separately mounted in main.py.
router = APIRouter(
    dependencies=[
        Depends(get_current_user_id),
        Depends(enforce_user_rate_limit),
    ]
)

router.include_router(cargo.router)
router.include_router(market.router)
router.include_router(forecasts.router)
router.include_router(freightos.router)
router.include_router(vessels.router)
router.include_router(feasibility.router)
router.include_router(port_constraints.router)
router.include_router(vessel_cargo_compatibility.router)
router.include_router(costs.router)
router.include_router(charter_scenarios.router)
router.include_router(risk.router)
router.include_router(decision.router)
router.include_router(human_decision.router)
router.include_router(outcomes.router)
router.include_router(model_evaluation.router)
