"""Unit tests for AuthService."""

import pytest

from core.exceptions import (
    AccountLockedError,
    AuthenticationError,
    InvalidCredentialsError,
    SetupAlreadyCompleteError,
)
from services.auth_service import AuthService


@pytest.mark.asyncio
async def test_is_setup_complete_false_initially(async_session):
    service = AuthService(async_session)
    assert await service.is_setup_complete() is False


@pytest.mark.asyncio
async def test_create_admin_then_setup_complete(async_session):
    service = AuthService(async_session)
    user = await service.create_admin("admin", "password123")
    assert user.username == "admin"
    assert await service.is_setup_complete() is True


@pytest.mark.asyncio
async def test_create_admin_twice_raises(async_session):
    service = AuthService(async_session)
    await service.create_admin("admin", "password123")
    with pytest.raises(SetupAlreadyCompleteError):
        await service.create_admin("other", "password123")


@pytest.mark.asyncio
async def test_authenticate_wrong_password_raises(async_session):
    service = AuthService(async_session)
    await service.create_admin("admin", "password123")
    with pytest.raises(InvalidCredentialsError):
        await service.authenticate("admin", "wrong")


@pytest.mark.asyncio
async def test_authenticate_unknown_user_raises(async_session):
    service = AuthService(async_session)
    with pytest.raises(InvalidCredentialsError):
        await service.authenticate("nobody", "password123")


@pytest.mark.asyncio
async def test_authenticate_correct_password_succeeds(async_session):
    service = AuthService(async_session)
    await service.create_admin("admin", "password123")
    user = await service.authenticate("admin", "password123")
    assert user.username == "admin"
    assert user.failed_attempts == 0


@pytest.mark.asyncio
async def test_lockout_after_max_attempts(async_session):
    service = AuthService(async_session)
    await service.create_admin("admin", "password123")

    for _ in range(5):
        with pytest.raises(InvalidCredentialsError):
            await service.authenticate("admin", "wrong")

    with pytest.raises(AccountLockedError):
        await service.authenticate("admin", "password123")


@pytest.mark.asyncio
async def test_session_lifecycle(async_session):
    service = AuthService(async_session)
    user = await service.create_admin("admin", "password123")

    token = await service.create_session(user.id)
    resolved = await service.validate_session(token)
    assert resolved.id == user.id

    await service.invalidate_session(token)
    with pytest.raises(AuthenticationError):
        await service.validate_session(token)


@pytest.mark.asyncio
async def test_validate_session_rejects_unknown_token(async_session):
    service = AuthService(async_session)
    with pytest.raises(AuthenticationError):
        await service.validate_session("not-a-real-token")


@pytest.mark.asyncio
async def test_change_password(async_session):
    service = AuthService(async_session)
    user = await service.create_admin("admin", "password123")

    with pytest.raises(InvalidCredentialsError):
        await service.change_password(user, "wrong-current", "new-password")

    await service.change_password(user, "password123", "new-password")
    reauthenticated = await service.authenticate("admin", "new-password")
    assert reauthenticated.id == user.id
