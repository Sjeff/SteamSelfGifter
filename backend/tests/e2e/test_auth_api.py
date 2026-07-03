"""End-to-end tests for the auth API: setup, login, sessions, lockout."""

import pytest
from httpx import AsyncClient

from api.dependencies import get_current_user
from api.main import app


@pytest.fixture(autouse=True)
def use_real_auth(test_client):
    """These tests exercise the real login flow, not the test-wide bypass.

    Depends on test_client so it runs after conftest's test_client fixture
    has installed the bypass override, and can remove it afterwards.
    """
    app.dependency_overrides.pop(get_current_user, None)
    yield


@pytest.mark.asyncio
async def test_status_before_and_after_setup(test_client: AsyncClient):
    response = await test_client.get("/api/v1/auth/status")
    assert response.json()["data"]["setup_complete"] is False

    await test_client.post(
        "/api/v1/auth/setup", json={"username": "admin", "password": "correct horse battery"}
    )

    response = await test_client.get("/api/v1/auth/status")
    assert response.json()["data"]["setup_complete"] is True


@pytest.mark.asyncio
async def test_setup_can_only_run_once(test_client: AsyncClient):
    first = await test_client.post(
        "/api/v1/auth/setup", json={"username": "admin", "password": "correct horse battery"}
    )
    assert first.status_code == 200

    second = await test_client.post(
        "/api/v1/auth/setup", json={"username": "someone-else", "password": "another password"}
    )
    assert second.status_code == 403


@pytest.mark.asyncio
async def test_setup_logs_you_in(test_client: AsyncClient):
    response = await test_client.post(
        "/api/v1/auth/setup", json={"username": "admin", "password": "correct horse battery"}
    )
    assert response.status_code == 200
    assert "session_token" in response.cookies

    me = await test_client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["data"]["username"] == "admin"


@pytest.mark.asyncio
async def test_login_wrong_password_rejected(test_client: AsyncClient):
    await test_client.post(
        "/api/v1/auth/setup", json={"username": "admin", "password": "correct horse battery"}
    )
    await test_client.post("/api/v1/auth/logout")

    response = await test_client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "wrong password"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_correct_password_succeeds(test_client: AsyncClient):
    await test_client.post(
        "/api/v1/auth/setup", json={"username": "admin", "password": "correct horse battery"}
    )
    await test_client.post("/api/v1/auth/logout")

    response = await test_client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "correct horse battery"}
    )
    assert response.status_code == 200
    assert "session_token" in response.cookies


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
async def test_me_without_cookie_is_unauthorized(test_client: AsyncClient):
    response = await test_client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_requires_session(test_client: AsyncClient):
    response = await test_client.get("/api/v1/system/health")
    assert response.status_code == 401


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
