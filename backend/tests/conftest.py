"""Shared pytest fixtures for all tests."""

import asyncio
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from core.config import settings
from models.base import Base
from models.user import User
from db.session import get_db
from api.dependencies import get_current_user, get_database
from api.main import app
from workers import scheduler as scheduler_module
from workers.scheduler import SchedulerManager


# The test client talks to the app over plain http (base_url="http://test"),
# so a Secure-flagged cookie would never be sent back — same as a real LAN
# deployment without TLS in front of it.
settings.session_cookie_secure = False


def _fake_current_user() -> User:
    """Stand-in for the logged-in user so existing tests don't need real auth."""
    return User(id=1, username="test-admin", password_hash="unused")


# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(autouse=True)
def reset_scheduler_global():
    """Reset the global scheduler_manager before and after each test.

    This ensures test isolation - each test gets a fresh scheduler instance
    that hasn't been started/stopped by other tests.
    """
    # Save the original scheduler_manager
    original_manager = scheduler_module.scheduler_manager

    # Create a fresh scheduler manager for this test
    scheduler_module.scheduler_manager = SchedulerManager()

    yield

    # Stop the test scheduler if running
    if scheduler_module.scheduler_manager.is_running:
        scheduler_module.scheduler_manager.stop(wait=False)

    # Restore the original
    scheduler_module.scheduler_manager = original_manager


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def async_engine():
    """Create async engine for each test function."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables after test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async session for each test."""
    async_session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def test_client(async_engine) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client with test database.

    Each request gets its own session, with auto-commit to persist data.
    """
    # Create session factory for test database
    async_session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=True,
    )

    # Override the get_db dependency - manually manage session lifecycle
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        session = async_session_maker()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    # Override both get_db and get_database to ensure all dependency paths work
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_database] = override_get_db
    # Existing tests predate auth and don't log in — treat every request as
    # already authenticated. test_api_routers_auth.py tests the real flow
    # by clearing this override.
    app.dependency_overrides[get_current_user] = _fake_current_user

    # Create async client
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    # Clear overrides after test
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def sync_test_client(async_engine) -> Generator[TestClient, None, None]:
    """Create synchronous test client for simpler tests."""

    # Create session factory for test database
    async_session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    # Override the get_db dependency - manually manage session lifecycle
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        session = async_session_maker()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    # Override both get_db and get_database
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_database] = override_get_db
    app.dependency_overrides[get_current_user] = _fake_current_user

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
