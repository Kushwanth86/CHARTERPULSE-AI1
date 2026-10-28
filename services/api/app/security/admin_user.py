from __future__ import annotations

from uuid import UUID

from fastapi import Depends, HTTPException, status

from services.api.app.config.settings import get_settings
from services.api.app.security.current_user import get_current_user_id


def get_admin_user_id(user_id: UUID = Depends(get_current_user_id)) -> UUID:
    """Authorize explicitly configured operators for shared reference-data writes.

    A blank or invalid allowlist fails closed. Do not use user_metadata or a
    caller-supplied role to grant privileged access.
    """
    configured = get_settings().admin_user_ids
    allowed: set[UUID] = set()
    for value in configured.split(","):
        candidate = value.strip()
        if not candidate:
            continue
        try:
            allowed.add(UUID(candidate))
        except ValueError:
            continue

    if user_id not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This operation requires an authorized CharterPulse administrator.",
        )
    return user_id
