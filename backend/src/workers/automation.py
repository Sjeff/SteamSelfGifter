"""Automation cycle worker.

Single unified job that performs all automated tasks in sequence:
1. Scan regular giveaways
2. Scan wishlist giveaways
3. Sync wins
4. Process eligible giveaways (enter them)
"""

from datetime import datetime, UTC
from typing import Dict, Any

import structlog

from db.session import AsyncSessionLocal
from services.giveaway_service import GiveawayService
from services.game_service import GameService
from services.settings_service import SettingsService
from services.notification_service import NotificationService
from services.scheduler_service import SchedulerService
from utils.steamgifts_client import SteamGiftsClient
from utils.steam_client import SteamClient
from core.events import event_manager

logger = structlog.get_logger()


async def automation_cycle(account_id: int = None) -> Dict[str, Any]:
    """
    Run a complete automation cycle for a specific account.

    Args:
        account_id: Account to run the cycle for. When None, uses the default account.

    Returns:
        Dictionary with cycle results.
    """
    start_time = datetime.now(UTC)

    logger.info("automation_cycle_started", account_id=account_id)

    results = {
        "account_id": account_id,
        "scan": {"new": 0, "updated": 0, "skipped": False},
        "wishlist": {"new": 0, "updated": 0, "skipped": False},
        "wins": {"new_wins": 0, "skipped": False},
        "entries": {"eligible": 0, "entered": 0, "failed": 0, "points_spent": 0, "skipped": False},
        "cycle_time": 0,
        "skipped": False,
    }

    async with AsyncSessionLocal() as session:
        # Check settings
        settings_service = SettingsService(session, account_id=account_id)
        settings = await settings_service.get_settings()
        # Resolve account_id from the returned account object
        account_id = settings.id

        # Skip if not authenticated
        if not settings.phpsessid:
            logger.warning("automation_cycle_skipped", reason="not_authenticated")
            results["skipped"] = True
            results["reason"] = "not_authenticated"
            return results

        # Create clients (shared across all operations)
        sg_client = SteamGiftsClient(
            phpsessid=settings.phpsessid,
            user_agent=settings.user_agent,
        )
        await sg_client.start()

        steam_client = SteamClient()
        await steam_client.start()

        # Create services (all scoped to this account)
        game_service = GameService(session=session, steam_client=steam_client)
        giveaway_service = GiveawayService(
            session=session,
            steamgifts_client=sg_client,
            game_service=game_service,
            account_id=account_id,
        )
        notification_service = NotificationService(session=session, account_id=account_id)
        scheduler_service = SchedulerService(
            session=session,
            giveaway_service=giveaway_service,
            account_id=account_id,
        )

        try:
            # === STEP 1: Scan regular giveaways ===
            logger.info("automation_step", step="scan_giveaways")
            max_pages = settings.max_scan_pages or 3

            try:
                new_count, updated_count = await giveaway_service.sync_giveaways(pages=max_pages)
                results["scan"] = {
                    "new": new_count,
                    "updated": updated_count,
                    "pages": max_pages,
                    "skipped": False,
                }
                await notification_service.log_scan_complete(
                    new_count=new_count,
                    updated_count=updated_count
                )
            except Exception as e:
                logger.error("scan_giveaways_failed", error=str(e))
                results["scan"]["error"] = str(e)
                await session.rollback()
                await notification_service.log_activity(
                    level="error",
                    event_type="scan",
                    message=f"Scan failed: {str(e)}",
                )

            # === STEP 2: Scan wishlist giveaways ===
            logger.info("automation_step", step="scan_wishlist")

            try:
                wishlist_new, wishlist_updated = await giveaway_service.sync_giveaways(
                    pages=1,
                    giveaway_type="wishlist"
                )
                results["wishlist"] = {
                    "new": wishlist_new,
                    "updated": wishlist_updated,
                    "skipped": False,
                }
            except Exception as e:
                logger.error("scan_wishlist_failed", error=str(e))
                results["wishlist"]["error"] = str(e)
                await session.rollback()
                await notification_service.log_activity(
                    level="error",
                    event_type="scan",
                    message=f"Wishlist scan failed: {str(e)}",
                )

            # === STEP 2.5: Scan DLC giveaways (if enabled) ===
            dlc_enabled = getattr(settings, 'dlc_enabled', False)
            if dlc_enabled:
                logger.info("automation_step", step="scan_dlc")
                results["dlc"] = {"new": 0, "updated": 0, "skipped": False}

                try:
                    dlc_new, dlc_updated = await giveaway_service.sync_giveaways(
                        pages=1,
                        dlc_only=True
                    )
                    results["dlc"] = {
                        "new": dlc_new,
                        "updated": dlc_updated,
                        "skipped": False,
                    }
                    logger.info("scan_dlc_completed", new=dlc_new, updated=dlc_updated)
                except Exception as e:
                    logger.error("scan_dlc_failed", error=str(e))
                    results["dlc"]["error"] = str(e)
                    await session.rollback()
                    await notification_service.log_activity(
                        level="error",
                        event_type="scan",
                        message=f"DLC scan failed: {str(e)}",
                    )
            else:
                results["dlc"] = {"skipped": True, "reason": "dlc_disabled"}

            # === STEP 3: Sync wins ===
            logger.info("automation_step", step="sync_wins")

            try:
                new_wins = await giveaway_service.sync_wins(pages=1)
                results["wins"] = {
                    "new_wins": new_wins,
                    "skipped": False,
                }
                if new_wins > 0:
                    logger.info("new_wins_detected", count=new_wins)
                    await notification_service.log_activity(
                        level="info",
                        event_type="win",
                        message=f"Detected {new_wins} new win(s)!",
                    )
            except Exception as e:
                logger.error("sync_wins_failed", error=str(e))
                results["wins"]["error"] = str(e)
                await session.rollback()
                await notification_service.log_activity(
                    level="error",
                    event_type="win",
                    message=f"Win sync failed: {str(e)}",
                )

            # === STEP 3.5: Sync entered giveaways ===
            logger.info("automation_step", step="sync_entered")
            results["entered_sync"] = {"synced": 0, "skipped": False}

            try:
                synced = await giveaway_service.sync_entered_giveaways(pages=1)
                results["entered_sync"] = {
                    "synced": synced,
                    "skipped": False,
                }
                if synced > 0:
                    logger.info("entered_giveaways_synced", count=synced)
            except Exception as e:
                logger.error("sync_entered_failed", error=str(e))
                results["entered_sync"]["error"] = str(e)
                await session.rollback()
                await notification_service.log_activity(
                    level="error",
                    event_type="scan",
                    message=f"Entered giveaways sync failed: {str(e)}",
                )

            # === STEP 4: Process entries ===
            logger.info("automation_step", step="process_entries")

            # Only process if autojoin is enabled
            if not settings.autojoin_enabled:
                results["entries"]["skipped"] = True
                results["entries"]["reason"] = "autojoin_disabled"
            else:
                try:
                    from workers.processor import _process_entries
                    entry_results = await _process_entries(
                        giveaway_service=giveaway_service,
                        notification_service=notification_service,
                        settings=settings,
                    )
                    results["entries"] = entry_results

                    # Schedule win check if we entered any giveaways
                    if entry_results.get("entered", 0) > 0:
                        await scheduler_service.schedule_next_win_check()

                except Exception as e:
                    logger.error("process_entries_failed", error=str(e))
                    results["entries"]["error"] = str(e)
                    await notification_service.log_activity(
                        level="error",
                        event_type="entry",
                        message=f"Entry processing failed: {str(e)}",
                    )

            # Calculate total cycle time
            end_time = datetime.now(UTC)
            results["cycle_time"] = round((end_time - start_time).total_seconds(), 2)

            logger.info(
                "automation_cycle_completed",
                account_id=account_id,
                scan_new=results["scan"]["new"],
                scan_updated=results["scan"]["updated"],
                wishlist_new=results["wishlist"]["new"],
                new_wins=results["wins"]["new_wins"],
                entries_entered=results["entries"].get("entered", 0),
                cycle_time=results["cycle_time"],
            )

            # Emit completion event (includes account_id for frontend filtering)
            await event_manager.broadcast_event("automation_cycle_completed", results)

            return results

        except Exception as e:
            logger.error(
                "automation_cycle_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            await event_manager.broadcast_event("automation_cycle_failed", {"error": str(e)})
            raise

        finally:
            await sg_client.close()
            await steam_client.close()


async def sync_wins_only(account_id: int = None) -> Dict[str, Any]:
    """
    Sync wins only (manual trigger) for a specific account.

    Args:
        account_id: Account to sync wins for. None = default account.

    Returns:
        Dictionary with win sync results
    """
    logger.info("sync_wins_started", account_id=account_id)

    async with AsyncSessionLocal() as session:
        settings_service = SettingsService(session, account_id=account_id)
        settings = await settings_service.get_settings()
        account_id = settings.id  # Resolve to concrete account ID

        if not settings.phpsessid:
            return {"new_wins": 0, "skipped": True, "reason": "not_authenticated"}

        sg_client = SteamGiftsClient(
            phpsessid=settings.phpsessid,
            user_agent=settings.user_agent,
        )
        await sg_client.start()

        steam_client = SteamClient()
        await steam_client.start()

        game_service = GameService(session=session, steam_client=steam_client)
        giveaway_service = GiveawayService(
            session=session,
            steamgifts_client=sg_client,
            game_service=game_service,
            account_id=account_id,
        )

        try:
            new_wins = await giveaway_service.sync_wins(pages=1)

            logger.info("sync_wins_completed", new_wins=new_wins)

            return {
                "new_wins": new_wins,
                "skipped": False,
            }

        finally:
            await sg_client.close()
            await steam_client.close()
