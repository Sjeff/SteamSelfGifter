"""Account service for multi-account management."""

from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from repositories.account import AccountRepository
from models.account import Account
from utils.steamgifts_client import SteamGiftsClient
from core.exceptions import SteamGiftsAuthError, SteamGiftsError, ResourceNotFoundError


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Fedora; Linux x86_64; rv:82.0) Gecko/20100101 Firefox/82.0"
)


class AccountService:
    """
    Service for managing multiple SteamGifts accounts.

    Handles CRUD operations, credential management, and session testing
    for individual accounts.

    Usage:
        >>> service = AccountService(session)
        >>> accounts = await service.list_accounts()
        >>> account = await service.create_account(name="Alt", phpsessid="...")
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AccountRepository(session)

    async def list_accounts(self) -> List[Account]:
        """Get all active accounts."""
        return await self.repo.get_all_active()

    async def list_active_accounts(self) -> List[Account]:
        """Get all active accounts."""
        return await self.repo.get_all_active()

    async def get_account(self, account_id: int) -> Account:
        """
        Get account by ID.

        Raises:
            ResourceNotFoundError: If account not found
        """
        account = await self.repo.get_by_id(account_id)
        if not account:
            raise ResourceNotFoundError(f"Account {account_id} not found")
        return account

    async def get_default_account(self) -> Account:
        """Get the default account (creates one if none exists)."""
        return await self.repo.get_default()

    async def get_account_or_default(self, account_id: Optional[int]) -> Account:
        """Get the specified account, or the default account if account_id is None."""
        if account_id is not None:
            return await self.get_account(account_id)
        return await self.get_default_account()

    async def create_account(
        self,
        name: str,
        phpsessid: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Account:
        """
        Create a new account.

        Args:
            name: Display name for the account
            phpsessid: Optional SteamGifts session cookie
            user_agent: Optional browser user agent

        Returns:
            Created Account
        """
        if not name or not name.strip():
            raise ValueError("Account name cannot be empty")

        account = await self.repo.create(
            name=name.strip(),
            is_active=True,
            is_default=False,
            phpsessid=phpsessid.strip() if phpsessid else None,
            user_agent=user_agent or DEFAULT_USER_AGENT,
        )
        await self.session.commit()
        return account

    async def update_account(self, account_id: int, **kwargs) -> Account:
        """
        Update account fields with validation.

        Args:
            account_id: Account to update
            **kwargs: Fields to update

        Returns:
            Updated Account
        """
        account = await self.get_account(account_id)

        # Validate name if being updated
        if "name" in kwargs:
            name = kwargs["name"]
            if not name or not name.strip():
                raise ValueError("Account name cannot be empty")
            kwargs["name"] = name.strip()

        # Validate phpsessid if being updated
        if "phpsessid" in kwargs and kwargs["phpsessid"]:
            kwargs["phpsessid"] = kwargs["phpsessid"].strip()

        # Validate autojoin settings
        if "autojoin_min_price" in kwargs:
            min_price = kwargs["autojoin_min_price"]
            if min_price is not None and min_price < 0:
                raise ValueError("autojoin_min_price must be >= 0")

        if "autojoin_min_score" in kwargs:
            min_score = kwargs["autojoin_min_score"]
            if min_score is not None and not (0 <= min_score <= 10):
                raise ValueError("autojoin_min_score must be between 0 and 10")

        if "autojoin_min_reviews" in kwargs:
            min_reviews = kwargs["autojoin_min_reviews"]
            if min_reviews is not None and min_reviews < 0:
                raise ValueError("autojoin_min_reviews must be >= 0")

        if "max_scan_pages" in kwargs:
            max_pages = kwargs["max_scan_pages"]
            if max_pages is not None and max_pages < 1:
                raise ValueError("max_scan_pages must be >= 1")

        if "max_entries_per_cycle" in kwargs:
            max_entries = kwargs["max_entries_per_cycle"]
            if max_entries is not None and max_entries < 1:
                raise ValueError("max_entries_per_cycle must be >= 1")

        if "entry_delay_min" in kwargs:
            delay_min = kwargs["entry_delay_min"]
            if delay_min is not None and delay_min < 0:
                raise ValueError("entry_delay_min must be >= 0")

        if "entry_delay_max" in kwargs:
            delay_max = kwargs["entry_delay_max"]
            if delay_max is not None and delay_max < 0:
                raise ValueError("entry_delay_max must be >= 0")

        # Validate delay range
        delay_min = kwargs.get("entry_delay_min", account.entry_delay_min)
        delay_max = kwargs.get("entry_delay_max", account.entry_delay_max)
        if delay_min is not None and delay_max is not None and delay_min > delay_max:
            raise ValueError("entry_delay_min must be <= entry_delay_max")

        updated = await self.repo.update_account(account_id, **kwargs)
        await self.session.commit()
        return updated

    async def set_credentials(
        self,
        account_id: int,
        phpsessid: str,
        user_agent: Optional[str] = None,
    ) -> Account:
        """
        Set SteamGifts credentials for an account.

        Args:
            account_id: Account to update
            phpsessid: SteamGifts PHPSESSID cookie
            user_agent: Optional browser user agent

        Returns:
            Updated Account
        """
        if not phpsessid or not phpsessid.strip():
            raise ValueError("phpsessid cannot be empty")

        updates: Dict[str, Any] = {"phpsessid": phpsessid.strip()}
        if user_agent:
            updates["user_agent"] = user_agent

        return await self.update_account(account_id, **updates)

    async def clear_credentials(self, account_id: int) -> Account:
        """Clear SteamGifts credentials for an account."""
        return await self.update_account(
            account_id,
            phpsessid=None,
            user_agent=DEFAULT_USER_AGENT,
            xsrf_token=None,
        )

    async def delete_account(self, account_id: int) -> bool:
        """
        Soft-delete an account (marks as inactive).

        Returns:
            True if deleted, False if it's the last account
        """
        result = await self.repo.delete_account(account_id)
        if result:
            await self.session.commit()
        return result

    async def set_default(self, account_id: int) -> Account:
        """Set an account as the default."""
        account = await self.repo.set_default(account_id)
        if not account:
            raise ResourceNotFoundError(f"Account {account_id} not found")
        await self.session.commit()
        return account

    async def test_session(self, account_id: int) -> Dict[str, Any]:
        """
        Test if the account's PHPSESSID is valid.

        Returns:
            Dict with valid, username, points (if valid), or error
        """
        account = await self.get_account(account_id)

        if not account.phpsessid:
            return {"valid": False, "error": "PHPSESSID not configured"}

        try:
            client = SteamGiftsClient(
                phpsessid=account.phpsessid,
                user_agent=account.user_agent,
                xsrf_token=account.xsrf_token,
            )

            async with client:
                user_info = await client.get_user_info()

                # Cache the XSRF token
                if client.xsrf_token and client.xsrf_token != account.xsrf_token:
                    await self.repo.update_account(account_id, xsrf_token=client.xsrf_token)
                    await self.session.commit()

                return {
                    "valid": True,
                    "username": user_info["username"],
                    "points": user_info["points"],
                }

        except SteamGiftsAuthError as e:
            return {"valid": False, "error": str(e)}
        except SteamGiftsError as e:
            return {"valid": False, "error": f"SteamGifts error: {e}"}
        except Exception as e:
            return {"valid": False, "error": f"Connection error: {e}"}

    async def validate_configuration(self, account_id: int) -> Dict[str, Any]:
        """Validate an account's configuration."""
        account = await self.get_account(account_id)
        errors = []
        warnings = []

        if not account.phpsessid:
            errors.append("SteamGifts PHPSESSID not configured")

        if account.autojoin_enabled:
            if account.autojoin_min_price is None:
                warnings.append("autojoin_min_price not set, will use 0")

        if account.automation_enabled and not account.phpsessid:
            errors.append("Cannot enable automation without PHPSESSID")

        if account.entry_delay_min and account.entry_delay_max:
            if account.entry_delay_min > account.entry_delay_max:
                errors.append(
                    f"entry_delay_min ({account.entry_delay_min}) > "
                    f"entry_delay_max ({account.entry_delay_max})"
                )

        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    async def reset_to_defaults(self, account_id: int) -> Account:
        """Reset automation settings to defaults while keeping credentials."""
        account = await self.get_account(account_id)
        return await self.update_account(
            account_id,
            # Keep credentials
            phpsessid=account.phpsessid,
            user_agent=account.user_agent,
            xsrf_token=account.xsrf_token,
            # Reset everything else
            dlc_enabled=False,
            autojoin_enabled=False,
            autojoin_start_at=350,
            autojoin_stop_at=200,
            autojoin_min_price=10,
            autojoin_min_score=7,
            autojoin_min_reviews=1000,
            autojoin_max_game_age=None,
            scan_interval_minutes=30,
            max_entries_per_cycle=None,
            automation_enabled=False,
            max_scan_pages=3,
            entry_delay_min=8,
            entry_delay_max=12,
        )
