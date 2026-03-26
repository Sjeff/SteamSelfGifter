"""Settings service — compatibility shim delegating to AccountRepository.

All existing callers (workers, API routers) continue to work unchanged.
When account_id is None, operates on the default account.
"""

from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from repositories.account import AccountRepository
from models.account import Account
from utils.steamgifts_client import SteamGiftsClient
from core.exceptions import SteamGiftsAuthError, SteamGiftsError

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Fedora; Linux x86_64; rv:82.0) Gecko/20100101 Firefox/82.0"
)


class SettingsService:
    """
    Backward-compatible settings service.

    Now delegates to AccountRepository instead of SettingsRepository.
    All existing method signatures are preserved.

    The optional account_id parameter allows workers to operate on a
    specific account. When None, operates on the default account.

    Usage:
        >>> service = SettingsService(session)                # default account
        >>> service = SettingsService(session, account_id=2)  # specific account
        >>> settings = await service.get_settings()           # returns Account object
    """

    def __init__(self, session: AsyncSession, account_id: Optional[int] = None):
        self.session = session
        self.account_id = account_id
        self.repo = AccountRepository(session)

    async def get_settings(self) -> Account:
        """
        Get settings. Returns Account object (same fields as old Settings).

        When account_id is set, returns that account.
        Otherwise returns the default account.
        """
        if self.account_id is not None:
            account = await self.repo.get_by_id(self.account_id)
            if account is None:
                # Fall back to default
                return await self.repo.get_default()
            return account
        return await self.repo.get_default()

    async def update_settings(self, **kwargs) -> Account:
        """Update settings with validation. Operates on the target account."""
        account = await self.get_settings()

        # Validate
        if "autojoin_min_price" in kwargs:
            if kwargs["autojoin_min_price"] is not None and kwargs["autojoin_min_price"] < 0:
                raise ValueError("autojoin_min_price must be >= 0")

        if "autojoin_min_score" in kwargs:
            s = kwargs["autojoin_min_score"]
            if s is not None and not (0 <= s <= 10):
                raise ValueError("autojoin_min_score must be between 0 and 10")

        if "autojoin_min_reviews" in kwargs:
            if kwargs["autojoin_min_reviews"] is not None and kwargs["autojoin_min_reviews"] < 0:
                raise ValueError("autojoin_min_reviews must be >= 0")

        if "max_scan_pages" in kwargs:
            if kwargs["max_scan_pages"] is not None and kwargs["max_scan_pages"] < 1:
                raise ValueError("max_scan_pages must be >= 1")

        if "max_entries_per_cycle" in kwargs:
            if kwargs["max_entries_per_cycle"] is not None and kwargs["max_entries_per_cycle"] < 1:
                raise ValueError("max_entries_per_cycle must be >= 1")

        if "entry_delay_min" in kwargs:
            if kwargs["entry_delay_min"] is not None and kwargs["entry_delay_min"] < 0:
                raise ValueError("entry_delay_min must be >= 0")

        if "entry_delay_max" in kwargs:
            if kwargs["entry_delay_max"] is not None and kwargs["entry_delay_max"] < 0:
                raise ValueError("entry_delay_max must be >= 0")

        delay_min = kwargs.get("entry_delay_min", account.entry_delay_min)
        delay_max = kwargs.get("entry_delay_max", account.entry_delay_max)
        if delay_min is not None and delay_max is not None and delay_min > delay_max:
            raise ValueError("entry_delay_min must be <= entry_delay_max")

        updated = await self.repo.update(account.id, **kwargs)
        return updated

    async def set_steamgifts_credentials(
        self, phpsessid: str, user_agent: Optional[str] = None
    ) -> Account:
        """Set SteamGifts credentials."""
        if not phpsessid or not phpsessid.strip():
            raise ValueError("phpsessid cannot be empty")

        account = await self.get_settings()
        updates = {"phpsessid": phpsessid.strip()}
        if user_agent:
            updates["user_agent"] = user_agent

        return await self.repo.update(account.id, **updates)

    async def clear_steamgifts_credentials(self) -> Account:
        """Clear SteamGifts credentials."""
        account = await self.get_settings()
        return await self.repo.update(
            account.id,
            phpsessid=None,
            user_agent=DEFAULT_USER_AGENT,
            xsrf_token=None,
        )

    async def is_authenticated(self) -> bool:
        """Check if SteamGifts credentials are configured."""
        account = await self.get_settings()
        return bool(account.phpsessid and account.phpsessid.strip())

    async def get_autojoin_config(self) -> Dict[str, Any]:
        """Get autojoin configuration as a dictionary."""
        account = await self.get_settings()
        return {
            "enabled": account.autojoin_enabled,
            "start_at": account.autojoin_start_at,
            "stop_at": account.autojoin_stop_at,
            "min_price": account.autojoin_min_price,
            "min_score": account.autojoin_min_score,
            "min_reviews": account.autojoin_min_reviews,
        }

    async def get_scheduler_config(self) -> Dict[str, Any]:
        """Get scheduler configuration as a dictionary."""
        account = await self.get_settings()
        return {
            "automation_enabled": account.automation_enabled,
            "scan_interval_minutes": account.scan_interval_minutes,
            "max_entries_per_cycle": account.max_entries_per_cycle,
            "entry_delay_min": account.entry_delay_min,
            "entry_delay_max": account.entry_delay_max,
            "max_scan_pages": account.max_scan_pages,
        }

    async def reset_to_defaults(self) -> Account:
        """Reset all settings to default values (keeps credentials)."""
        account = await self.get_settings()
        return await self.repo.update(
            account.id,
            phpsessid=account.phpsessid,
            user_agent=account.user_agent,
            xsrf_token=account.xsrf_token,
            dlc_enabled=False,
            autojoin_enabled=False,
            autojoin_start_at=350,
            autojoin_stop_at=200,
            autojoin_min_price=10,
            autojoin_min_score=7,
            autojoin_min_reviews=1000,
            scan_interval_minutes=30,
            max_entries_per_cycle=None,
            automation_enabled=False,
            max_scan_pages=3,
            entry_delay_min=8,
            entry_delay_max=12,
        )

    async def validate_configuration(self) -> Dict[str, Any]:
        """Validate current configuration."""
        account = await self.get_settings()
        errors = []
        warnings = []

        if not account.phpsessid:
            errors.append("SteamGifts PHPSESSID not configured")

        if account.autojoin_enabled and account.autojoin_min_price is None:
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

    async def test_session(self) -> Dict[str, Any]:
        """Test if the configured PHPSESSID is valid."""
        account = await self.get_settings()

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

                if client.xsrf_token and client.xsrf_token != account.xsrf_token:
                    await self.repo.update(account.id, xsrf_token=client.xsrf_token)

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
