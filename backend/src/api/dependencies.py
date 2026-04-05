"""FastAPI dependency injection for database sessions and services.

This module provides dependency functions for FastAPI endpoints,
enabling clean dependency injection of database sessions and service layers.
"""

from typing import Annotated, Optional
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from db.session import get_db
from services.settings_service import SettingsService
from services.notification_service import NotificationService
from services.game_service import GameService
from services.giveaway_service import GiveawayService
from services.scheduler_service import SchedulerService
from services.account_service import AccountService
from utils.steam_client import SteamClient
from utils.steamgifts_client import SteamGiftsClient

logger = structlog.get_logger()


# Database session dependency
# This is re-exported from db.session for convenience
async def get_database() -> AsyncSession:
    """
    Get database session dependency.

    Re-exports get_db from db.session for API layer use.

    Yields:
        AsyncSession: Database session

    Example:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_database)):
            ...
    """
    async for session in get_db():
        yield session


# Type aliases for cleaner endpoint signatures
DatabaseDep = Annotated[AsyncSession, Depends(get_database)]


# Service dependencies
def get_settings_service(db: DatabaseDep, account_id: Optional[int] = None) -> SettingsService:
    """
    Get SettingsService dependency.

    Args:
        db: Database session from dependency injection
        account_id: Optional account ID to scope to (from query param)

    Returns:
        SettingsService instance

    Example:
        @router.get("/settings")
        async def get_settings(
            settings_service: SettingsService = Depends(get_settings_service)
        ):
            return await settings_service.get_settings()
    """
    return SettingsService(db, account_id=account_id)


def get_notification_service(db: DatabaseDep, account_id: Optional[int] = None) -> NotificationService:
    """
    Get NotificationService dependency.

    Args:
        db: Database session from dependency injection
        account_id: Optional account ID to scope logs to

    Returns:
        NotificationService instance

    Example:
        @router.get("/logs")
        async def get_logs(
            notification_service: NotificationService = Depends(get_notification_service)
        ):
            return await notification_service.get_recent_logs()
    """
    return NotificationService(db, account_id=account_id)


# Type aliases for service dependencies (for cleaner endpoint signatures)
SettingsServiceDep = Annotated[SettingsService, Depends(get_settings_service)]
NotificationServiceDep = Annotated[NotificationService, Depends(get_notification_service)]


async def get_game_service(db: DatabaseDep) -> GameService:
    """
    Get GameService dependency.

    Creates a GameService with SteamClient for Steam API access.

    Args:
        db: Database session from dependency injection

    Returns:
        GameService instance

    Example:
        @router.get("/games/{app_id}")
        async def get_game(
            app_id: int,
            game_service: GameService = Depends(get_game_service)
        ):
            return await game_service.get_or_fetch_game(app_id)
    """
    steam_client = SteamClient()
    await steam_client.start()
    return GameService(db, steam_client)


def get_account_service(db: DatabaseDep) -> AccountService:
    """Get AccountService dependency."""
    return AccountService(db)


AccountServiceDep = Annotated[AccountService, Depends(get_account_service)]


async def get_giveaway_service(
    db: DatabaseDep,
    account_id: Optional[int] = None,
) -> GiveawayService:
    """
    Get GiveawayService dependency.

    When account_id is provided (via query param), uses that account.
    Otherwise uses the default account.

    Args:
        db: Database session from dependency injection
        account_id: Optional account ID to scope to

    Returns:
        GiveawayService instance scoped to the account
    """
    # Get account settings for credentials
    settings_service = SettingsService(db, account_id=account_id)
    settings = await settings_service.get_settings()
    resolved_account_id = settings.id

    # Create SteamGifts client (may not be authenticated)
    sg_client = SteamGiftsClient(
        phpsessid=settings.phpsessid or "",
        user_agent=settings.user_agent,
    )
    try:
        await sg_client.start()
    except Exception as e:
        # Session may be expired or invalid — log and continue.
        # Read-only DB endpoints (e.g. /won, /giveaways) still work;
        # SteamGifts HTTP operations will fail when actually attempted.
        logger.warning("steamgifts_client_start_failed", account_id=resolved_account_id, error=str(e))

    # Create Steam client for game data
    steam_client = SteamClient()
    await steam_client.start()

    # Create game service
    game_service = GameService(db, steam_client)

    return GiveawayService(db, sg_client, game_service, account_id=resolved_account_id)


async def get_scheduler_service(
    db: DatabaseDep,
    account_id: Optional[int] = None,
) -> SchedulerService:
    """
    Get SchedulerService dependency.

    Args:
        db: Database session from dependency injection
        account_id: Optional account ID to scope to

    Returns:
        SchedulerService instance
    """
    giveaway_service = await get_giveaway_service(db, account_id=account_id)
    return SchedulerService(db, giveaway_service, account_id=account_id)


# Type aliases for new service dependencies
GameServiceDep = Annotated[GameService, Depends(get_game_service)]
GiveawayServiceDep = Annotated[GiveawayService, Depends(get_giveaway_service)]
SchedulerServiceDep = Annotated[SchedulerService, Depends(get_scheduler_service)]


# Example usage in routers:
"""
from api.dependencies import DatabaseDep, SettingsServiceDep

@router.get("/settings")
async def get_settings(settings_service: SettingsServiceDep):
    '''Get application settings.'''
    settings = await settings_service.get_settings()
    return create_success_response(data=settings)

# Or using the underlying dependency function:
@router.get("/settings")
async def get_settings(
    settings_service: SettingsService = Depends(get_settings_service)
):
    '''Get application settings.'''
    settings = await settings_service.get_settings()
    return create_success_response(data=settings)

# Direct database access if needed:
@router.get("/custom")
async def custom_endpoint(db: DatabaseDep):
    '''Custom endpoint with direct database access.'''
    result = await db.execute(select(Model))
    return result.scalars().all()
"""
