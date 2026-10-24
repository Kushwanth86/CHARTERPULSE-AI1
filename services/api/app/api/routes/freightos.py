from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from services.api.app.services.freightos_service import (
    FreightosNoQuoteError,
    FreightosRateLimitError,
    FreightosService,
    FreightosServiceError,
)


router = APIRouter(
    prefix="/api/v1/freightos",
    tags=["freightos"],
)

freightos_service = FreightosService()


@router.get("/estimate")
def get_container_estimate(
    origin: str = Query(..., min_length=2, max_length=30),
    destination: str = Query(..., min_length=2, max_length=30),
    loadtype: Literal[
        "container20",
        "container40",
        "container40HC",
        "container45",
        "container45HC",
    ] = "container40",
    quantity: int = Query(1, ge=1, le=20),
    weight: float | None = Query(None, gt=0),
):
    try:
        return freightos_service.estimate(
            origin=origin,
            destination=destination,
            loadtype=loadtype,
            quantity=quantity,
            weight=weight,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except FreightosNoQuoteError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FreightosRateLimitError as exc:
        return JSONResponse(
            status_code=429,
            content={"detail": str(exc)},
            headers={"Retry-After": str(exc.retry_after)},
        )
    except FreightosServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
