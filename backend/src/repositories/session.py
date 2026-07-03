"""Session repository for server-side login sessions."""

from datetime import datetime
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.session import AuthSession
from repositories.base import BaseRepository


class SessionRepository(BaseRepository[AuthSession]):
    """Repository for the AuthSession model."""

    def __init__(self, session: AsyncSession):
        super().__init__(AuthSession, session)

    async def get_by_token_hash(self, token_hash: str) -> Optional[AuthSession]:
        """Get a session by its token hash."""
        result = await self.session.execute(
            select(AuthSession).where(AuthSession.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def delete_by_token_hash(self, token_hash: str) -> None:
        """Invalidate a session by its token hash (used on logout)."""
        await self.session.execute(delete(AuthSession).where(AuthSession.token_hash == token_hash))
        await self.session.flush()

    async def delete_expired(self, now: datetime) -> None:
        """Remove sessions that have already expired."""
        await self.session.execute(delete(AuthSession).where(AuthSession.expires_at < now))
        await self.session.flush()
