from __future__ import annotations

import math
import threading
import time
from collections import defaultdict, deque
from uuid import UUID

from fastapi import HTTPException, Request, status


_WINDOW_SECONDS = 60.0
_DEFAULT_LIMIT = 120
_PATH_LIMITS: tuple[tuple[str, int], ...] = (
    ("/api/v1/freightos/estimate", 8),
    ("/api/v1/decision/evaluate", 10),
    ("/api/v1/forecasts/freight", 10),
    ("/api/v1/feasibility", 10),
    ("/api/v1/model-evaluations/forecast", 10),
    ("/api/v1/market/observations", 30),
)
_events: dict[tuple[str, str], deque[float]] = defaultdict(deque)
_lock = threading.Lock()


def enforce_user_rate_limit(request: Request, user_id: UUID) -> None:
    """Bound request volume per authenticated user and route class.

    This in-process limiter is appropriate only while the service runs as one
    worker/instance. Before scaling to multiple instances, replace it with a
    shared atomic limiter (for example Redis or a Postgres RPC) so a caller
    cannot multiply the quota by hitting different workers.
    """
    path = request.url.path
    bucket = "default"
    limit = _DEFAULT_LIMIT
    for prefix, prefix_limit in _PATH_LIMITS:
        if path == prefix or path.startswith(prefix + "/"):
            bucket = prefix
            limit = prefix_limit
            break

    now = time.monotonic()
    key = (str(user_id), bucket)
    with _lock:
        history = _events[key]
        while history and now - history[0] >= _WINDOW_SECONDS:
            history.popleft()
        if len(history) >= limit:
            retry_after = max(1, math.ceil(_WINDOW_SECONDS - (now - history[0])))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded for this endpoint. Retry shortly.",
                headers={"Retry-After": str(retry_after)},
            )
        history.append(now)


def _reset_rate_limits_for_tests() -> None:
    with _lock:
        _events.clear()
