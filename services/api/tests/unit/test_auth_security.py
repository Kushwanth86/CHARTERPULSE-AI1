from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

from services.api.app.main import app
from services.api.app.security import current_user
from services.api.app.security.rate_limit import (
    _events,
    _reset_rate_limits_for_tests,
    enforce_user_rate_limit,
)


USER_ID = UUID("00000000-0000-4000-8000-000000000123")
OTHER_USER_ID = UUID("00000000-0000-4000-8000-000000000456")


def test_unauthenticated_v1_api_request_returns_401():
    client = TestClient(app)

    response = client.get("/api/v1/cargo")

    assert response.status_code == 401
    assert response.headers.get("www-authenticate") == "Bearer"


def test_missing_bearer_token_is_rejected_before_network_request(monkeypatch):
    def forbidden_request(*args, **kwargs):
        raise AssertionError("An absent token must not call Supabase Auth.")

    monkeypatch.setattr(current_user.httpx, "get", forbidden_request)

    with pytest.raises(HTTPException) as exc:
        current_user.get_current_user_id(None)

    assert exc.value.status_code == 401


def test_current_user_is_derived_from_verified_supabase_auth_response(monkeypatch):
    calls = []

    class Response:
        status_code = 200

        @staticmethod
        def json():
            return {"id": str(USER_ID), "email": "user@example.invalid"}

    def fake_get(url, *, headers, timeout, follow_redirects):
        calls.append((url, headers, timeout, follow_redirects))
        return Response()

    monkeypatch.setattr(current_user.httpx, "get", fake_get)
    monkeypatch.setattr(
        current_user,
        "get_settings",
        lambda: SimpleNamespace(
            supabase_url="https://example-project.supabase.co/",
            supabase_publishable_key="sb_publishable_test",
        ),
    )

    result = current_user.get_current_user_id(
        HTTPAuthorizationCredentials(scheme="Bearer", credentials="test-access-token")
    )

    assert result == USER_ID
    assert calls[0][0] == "https://example-project.supabase.co/auth/v1/user"
    assert calls[0][1]["Authorization"] == "Bearer test-access-token"
    assert calls[0][1]["apikey"] == "sb_publishable_test"
    assert calls[0][2] == 5.0
    assert calls[0][3] is False


@pytest.mark.parametrize("status_code", [400, 401, 403, 404])
def test_invalid_or_revoked_token_is_401(monkeypatch, status_code):
    class Response:
        def __init__(self, status):
            self.status_code = status

    monkeypatch.setattr(current_user.httpx, "get", lambda *args, **kwargs: Response(status_code))
    monkeypatch.setattr(
        current_user,
        "get_settings",
        lambda: SimpleNamespace(
            supabase_url="https://example-project.supabase.co",
            supabase_publishable_key="sb_publishable_test",
        ),
    )

    with pytest.raises(HTTPException) as exc:
        current_user.get_current_user_id(
            HTTPAuthorizationCredentials(scheme="Bearer", credentials="expired-token")
        )
    assert exc.value.status_code == 401
    assert "expired-token" not in str(exc.value.detail)


def test_auth_service_outage_fails_closed_with_503(monkeypatch):
    import httpx

    monkeypatch.setattr(
        current_user.httpx,
        "get",
        lambda *args, **kwargs: (_ for _ in ()).throw(httpx.ConnectError("down")),
    )
    monkeypatch.setattr(
        current_user,
        "get_settings",
        lambda: SimpleNamespace(
            supabase_url="https://example-project.supabase.co",
            supabase_publishable_key="sb_publishable_test",
        ),
    )

    with pytest.raises(HTTPException) as exc:
        current_user.get_current_user_id(
            HTTPAuthorizationCredentials(scheme="Bearer", credentials="test-token")
        )
    assert exc.value.status_code == 503


def test_rate_limit_is_scoped_by_user_and_returns_retry_after():
    _reset_rate_limits_for_tests()
    request = SimpleNamespace(url=SimpleNamespace(path="/api/v1/freightos/estimate"))

    for _ in range(8):
        enforce_user_rate_limit(request, USER_ID)

    with pytest.raises(HTTPException) as exc:
        enforce_user_rate_limit(request, USER_ID)

    assert exc.value.status_code == 429
    assert int(exc.value.headers["Retry-After"]) >= 1

    # A second verified user receives their own budget.
    enforce_user_rate_limit(request, OTHER_USER_ID)
    _reset_rate_limits_for_tests()


def test_private_cargo_reads_are_filtered_by_verified_owner(monkeypatch):
    from services.api.app.repositories import cargo_repository

    queries = []

    class Query:
        def __init__(self, table):
            self.table = table
            self.filters = []
            queries.append(self)

        def select(self, _fields):
            return self

        def eq(self, key, value):
            self.filters.append((key, value))
            return self

        def limit(self, _limit):
            return self

        def execute(self):
            return SimpleNamespace(data=[])

    class Client:
        def table(self, name):
            return Query(name)

    monkeypatch.setattr(
        cargo_repository,
        "get_supabase_admin_client",
        lambda: Client(),
    )

    result = cargo_repository.CargoRepository().get(
        UUID("00000000-0000-4000-8000-000000000789"),
        USER_ID,
    )

    assert result is None
    assert queries[0].table == "cargo_requirements"
    assert ("user_id", str(USER_ID)) in queries[0].filters
    assert ("user_id", str(OTHER_USER_ID)) not in queries[0].filters
