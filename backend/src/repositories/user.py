"""User repository for app-level authentication."""

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for the User model."""

    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_username(self, username: str) -> Optional[User]:
        """Get a user by username (case-sensitive, usernames are unique)."""
        result = await self.session.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def count_users(self) -> int:
        """Count how many users exist, used to decide if setup is complete."""
        result = await self.session.execute(select(func.count()).select_from(User))
        return result.scalar_one()
