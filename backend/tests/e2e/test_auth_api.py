"""End-to-end tests for the auth API: setup, login, sessions, lockout."""

import pytest
from httpx import AsyncClient

from api.dependencies import get_current_user
from api.main import app
from core.config import settings


@pytest.fixture(autouse=True)
def use_real_auth(test_client):
    """These tests exercise the real login flow, not the test-wide bypass.

    Depends on test_client so it runs after conftest's test_client fixture
    has installed the bypass override, and can remove it afterwards.
    """
    app.dependency_overrides.pop(get_current_user, None)
    yield


@pytest.mark.asyncio
async def test_setup_flow(test_client: AsyncClient):
    status_before = await test_client.get("/api/v1/auth/status")
    assert status_before.json()["data"]["setup_complete"] is False

    setup_response = await test_client.post(
        "/api/v1/auth/setup", json={"username": "admin", "password": "correct horse battery"}
    )
    assert setup_response.status_code == 200
    assert "session_token" in setup_response.cookies

    me = await test_client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["data"]["username"] == "admin"

    status_after = await test_client.get("/api/v1/auth/status")
    assert status_after.json()["data"]["setup_complete"] is True

    second_setup = await test_client.post(
        "/api/v1/auth/setup", json={"username": "someone-else", "password": "another password"}
    )
    assert second_setup.status_code == 403


@pytest.mark.asyncio
async def test_login_flow(test_client: AsyncClient):
    await test_client.post(
        "/api/v1/auth/setup", json={"username": "admin", "password": "correct horse battery"}
    )
    await test_client.post("/api/v1/auth/logout")

    wrong = await test_client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "wrong password"}
    )
    assert wrong.status_code == 401

    correct = await test_client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "correct horse battery"}
    )
    assert correct.status_code == 200
    assert "session_token" in correct.cookies


@pytest.mark.asyncio
async def test_account_locks_after_repeated_failures(test_client: AsyncClient):
    await test_client.post(
        "/api/v1/auth/setup", json={"username": "admin", "password": "correct horse battery"}
    )
    await test_client.post("/api/v1/auth/logout")

    for _ in range(5):
        response = await test_client.post(
            "/api/v1/auth/login", json={"username": "admin", "password": "wrong password"}
        )
        assert response.status_code == 401

    # Even the correct password is now rejected while locked out.
    locked_response = await test_client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "correct horse battery"}
    )
    assert locked_response.status_code == 429


@pytest.mark.asyncio
async def test_requires_session(test_client: AsyncClient):
    """Both CurrentUserDep-as-parameter (auth router) and router-level
    dependencies=[...] (every other router) must reject unauthenticated requests.
    """
    me = await test_client.get("/api/v1/auth/me")
    assert me.status_code == 401

    other_router = await test_client.get("/api/v1/accounts")
    assert other_router.status_code == 401


@pytest.mark.asyncio
async def test_system_health_does_not_require_session(test_client: AsyncClient):
    """Reverse proxies/orchestrators health-check without a session cookie.

    Regression test: 3.1.0 accidentally put this behind login alongside the
    rest of the system router, breaking any pre-existing external healthcheck
    pointed at it.
    """
    response = await test_client.get("/api/v1/system/health")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "healthy"


@pytest.mark.asyncio
async def test_logout_invalidates_session(test_client: AsyncClient):
    await test_client.post(
        "/api/v1/auth/setup", json={"username": "admin", "password": "correct horse battery"}
    )
    await test_client.post("/api/v1/auth/logout")

    response = await test_client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_change_password_flow(test_client: AsyncClient):
    await test_client.post(
        "/api/v1/auth/setup", json={"username": "admin", "password": "correct horse battery"}
    )

    wrong_current = await test_client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "not it", "new_password": "new password 123"},
    )
    assert wrong_current.status_code == 401

    changed = await test_client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "correct horse battery", "new_password": "new password 123"},
    )
    assert changed.status_code == 200

    await test_client.post("/api/v1/auth/logout")

    old_password_login = await test_client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "correct horse battery"}
    )
    assert old_password_login.status_code == 401

    new_password_login = await test_client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "new password 123"}
    )
    assert new_password_login.status_code == 200


@pytest.mark.asyncio
async def test_setup_warns_when_secure_cookie_requested_over_http(
    test_client: AsyncClient, mocker
):
    """A Secure cookie over plain HTTP is silently dropped by the browser.

    Regression test: this exact misconfiguration (SESSION_COOKIE_SECURE=true
    with no TLS in front) looked like a successful login followed by every
    subsequent request being unauthenticated - it should be logged loudly
    instead of failing silently.
    """
    settings.session_cookie_secure = True
    warn = mocker.patch("api.routers.auth.logger.warning")
    try:
        response = await test_client.post(
            "/api/v1/auth/setup",
            json={"username": "admin", "password": "correct horse battery"},
        )
        assert response.status_code == 200
        assert warn.call_args[0][0] == "insecure_session_cookie_over_http"
    finally:
        settings.session_cookie_secure = False


@pytest.mark.asyncio
async def test_login_does_not_warn_when_secure_cookie_not_required(
    test_client: AsyncClient, mocker
):
    await test_client.post(
        "/api/v1/auth/setup", json={"username": "admin", "password": "correct horse battery"}
    )

    warn = mocker.patch("api.routers.auth.logger.warning")
    response = await test_client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "correct horse battery"}
    )

    assert response.status_code == 200
    warn.assert_not_called()
