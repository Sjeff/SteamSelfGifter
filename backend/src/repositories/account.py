"""Account repository for multi-account management."""

from typing import List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.account import Account
from repositories.base import BaseRepository


class AccountRepository(BaseRepository[Account]):
    """
    Repository for Account model.

    Provides methods for managing multiple SteamGifts accounts.
    Replaces the SettingsRepository singleton pattern.

    Usage:
        >>> repo = AccountRepository(session)
        >>> accounts = await repo.get_all_active()
        >>> default = await repo.get_default()
    """

    def __init__(self, session: AsyncSession):
        super().__init__(Account, session)

    async def get_all_active(self) -> List[Account]:
        """Get all active accounts."""
        result = await self.session.execute(
            select(Account).where(Account.is_active == True).order_by(Account.id)  # noqa: E712
        )
        return list(result.scalars().all())

    async def get_default(self) -> Account:
        """
        Get the default account, creating one if it doesn't exist.

        Returns:
            The default Account (marked with is_default=True)
        """
        result = await self.session.execute(
            select(Account).where(Account.is_default == True).limit(1)  # noqa: E712
        )
        account = result.scalar_one_or_none()

        if account is None:
            # First run or after reset - create a blank default account
            account = await self.create(
                name="Default",
                is_active=True,
                is_default=True,
            )
            await self.session.flush()

        return account

    async def set_default(self, account_id: int) -> Optional[Account]:
        """
        Set the specified account as the default, clearing all others.
        Uses atomic SQL UPDATE to avoid race conditions.

        Args:
            account_id: ID of the account to make default

        Returns:
            The updated account, or None if not found
        """
        account = await self.get_by_id(account_id)
        if not account:
            return None

        # Atomic: clear all defaults, then set the new one in two UPDATE statements
        await self.session.execute(update(Account).values(is_default=False))
        await self.session.execute(
            update(Account).where(Account.id == account_id).values(is_default=True)
        )
        await self.session.flush()

        # Refresh to reflect the updated state
        await self.session.refresh(account)
        return account

    async def get_all(self, limit=None, offset=None) -> List[Account]:
        """Get all accounts ordered by id."""
        result = await self.session.execute(
            select(Account).order_by(Account.id)
        )
        return list(result.scalars().all())

    async def update_account(self, account_id: int, **kwargs) -> Optional[Account]:
        """Update account fields."""
        return await self.update(account_id, **kwargs)

    async def delete_account(self, account_id: int) -> bool:
        """
        Soft-delete an account by marking it inactive.

        Does not hard-delete to preserve historical data (giveaways, entries, logs).
        Refuses to delete the last active account.

        Returns:
            True if deactivated, False if not found or last account
        """
        active = await self.get_all_active()
        if len(active) <= 1:
            return False  # Cannot delete the last account

        account = await self.get_by_id(account_id)
        if not account:
            return False

        account.is_active = False
        # If this was the default, promote the first remaining active account
        if account.is_default:
            remaining = [a for a in active if a.id != account_id]
            if remaining:
                remaining[0].is_default = True
        account.is_default = False
        await self.session.flush()
        return True
