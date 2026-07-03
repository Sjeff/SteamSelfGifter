"""Auth service: one-time admin setup, login sessions, and password changes."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.exceptions import (
    AccountLockedError,
    AuthenticationError,
    InvalidCredentialsError,
    SetupAlreadyCompleteError,
)
from models.user import User
from repositories.session import SessionRepository
from repositories.user import UserRepository

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class AuthService:
    """Service for the single-admin login flow."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = UserRepository(session)
        self.sessions = SessionRepository(session)

    async def is_setup_complete(self) -> bool:
        """Whether the one admin account has already been created."""
        return await self.users.count_users() > 0

    async def create_admin(self, username: str, password: str) -> User:
        """Create the one admin account. Fails if setup was already done."""
        if await self.is_setup_complete():
            raise SetupAlreadyCompleteError(
                message="Setup has already been completed",
                code="AUTH_004",
            )
        return await self.users.create(
            username=username,
            password_hash=_hash_password(password),
        )

    async def authenticate(self, username: str, password: str) -> User:
        """Verify credentials, applying lockout after repeated failures.

        Raises InvalidCredentialsError or AccountLockedError on failure.
        """
        user = await self.users.get_by_username(username)
        now = datetime.now(timezone.utc)

        if user is None:
            # Don't leak whether the username exists.
            raise InvalidCredentialsError(message="Invalid username or password", code="AUTH_002")

        if user.locked_until is not None and user.locked_until > now:
            raise AccountLockedError(
                message="Account temporarily locked due to repeated failed logins",
                code="AUTH_003",
                details={"locked_until": user.locked_until.isoformat()},
            )

        if not _verify_password(password, user.password_hash):
            user.failed_attempts += 1
            if user.failed_attempts >= MAX_FAILED_ATTEMPTS:
                user.locked_until = now + timedelta(minutes=LOCKOUT_MINUTES)
                user.failed_attempts = 0
            # Commit (not just flush): the caller raises right after this,
            # and get_db() rolls back the session on any exception, which
            # would otherwise silently discard the lockout counter.
            await self.session.commit()
            raise InvalidCredentialsError(message="Invalid username or password", code="AUTH_002")

        user.failed_attempts = 0
        user.locked_until = None
        await self.session.flush()
        return user

    async def create_session(self, user_id: int) -> str:
        """Create a session for the user and return the raw token for the cookie."""
        token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        await self.sessions.create(
            user_id=user_id,
            token_hash=_hash_token(token),
            expires_at=now + timedelta(hours=settings.session_lifetime_hours),
            created_at=now,
        )
        return token

    async def validate_session(self, token: str) -> User:
        """Resolve a session token to its user, raising AuthenticationError if invalid."""
        auth_session = await self.sessions.get_by_token_hash(_hash_token(token))
        if auth_session is None:
            raise AuthenticationError(message="Not authenticated", code="AUTH_001")

        if auth_session.expires_at < datetime.now(timezone.utc):
            await self.sessions.delete_by_token_hash(auth_session.token_hash)
            raise AuthenticationError(message="Session expired", code="AUTH_001")

        user = await self.users.get_by_id(auth_session.user_id)
        if user is None:
            raise AuthenticationError(message="Not authenticated", code="AUTH_001")
        return user

    async def invalidate_session(self, token: str) -> None:
        """Log out: delete the session server-side."""
        await self.sessions.delete_by_token_hash(_hash_token(token))

    async def change_password(self, user: User, current_password: str, new_password: str) -> None:
        """Change the current user's password after verifying the current one."""
        if not _verify_password(current_password, user.password_hash):
            raise InvalidCredentialsError(message="Current password is incorrect", code="AUTH_002")
        user.password_hash = _hash_password(new_password)
        await self.session.flush()
