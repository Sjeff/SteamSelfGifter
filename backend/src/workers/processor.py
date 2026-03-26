"""Giveaway processor worker.

Background job that processes eligible giveaways and enters them
automatically based on configured criteria.
"""

import asyncio
import random
from datetime import datetime, UTC
from typing import Dict, Any

import structlog

from db.session import AsyncSessionLocal
from services.giveaway_service import GiveawayService
from services.game_service import GameService
from services.settings_service import SettingsService
from services.notification_service import NotificationService
from utils.steamgifts_client import SteamGiftsClient
from utils.steam_client import SteamClient
from core.events import event_manager

logger = structlog.get_logger()


async def process_giveaways(account_id: int = None) -> Dict[str, Any]:
    """
    Process eligible giveaways and enter them automatically.

    This is the main processor job function that:
    1. Gets eligible giveaways based on settings criteria
    2. Enters them respecting limits and delays
    3. Tracks statistics and emits events

    Args:
        account_id: Account to process for. When None, uses the default account.

    Returns:
        Dictionary with processing results:
            - eligible: Number of eligible giveaways found
            - entered: Number of giveaways successfully entered
            - failed: Number of failed entries
            - points_spent: Total points spent
            - skipped: Whether processing was skipped

    Example:
        >>> results = await process_giveaways()
        >>> print(f"Entered {results['entered']} giveaways")
    """
    start_time = datetime.now(UTC)

    logger.info("giveaway_processing_started", account_id=account_id)

    async with AsyncSessionLocal() as session:
        # Check settings
        settings_service = SettingsService(session, account_id=account_id)
        settings = await settings_service.get_settings()
        account_id = settings.id

        # Skip if not authenticated
        if not settings.phpsessid:
            logger.warning("giveaway_processing_skipped", reason="not_authenticated")
            return {
                "eligible": 0,
                "entered": 0,
                "failed": 0,
                "points_spent": 0,
                "skipped": True,
                "reason": "not_authenticated",
            }

        # Skip if autojoin not enabled
        if not settings.autojoin_enabled:
            logger.info("giveaway_processing_skipped", reason="autojoin_disabled")
            return {
                "eligible": 0,
                "entered": 0,
                "failed": 0,
                "points_spent": 0,
                "skipped": True,
                "reason": "autojoin_disabled",
            }

        # Create clients
        sg_client = SteamGiftsClient(
            phpsessid=settings.phpsessid,
            user_agent=settings.user_agent,
        )
        await sg_client.start()

        steam_client = SteamClient()
        await steam_client.start()

        # Create services
        game_service = GameService(session=session, steam_client=steam_client)
        giveaway_service = GiveawayService(
            session=session,
            steamgifts_client=sg_client,
            game_service=game_service,
            account_id=account_id,
        )
        notification_service = NotificationService(session=session, account_id=account_id)

        try:
            # Check current points before starting
            start_at = settings.autojoin_start_at or 0
            stop_at = settings.autojoin_stop_at or 0
            current_points = await giveaway_service.get_current_points()

            if start_at > 0 and current_points < start_at:
                logger.info(
                    "giveaway_processing_skipped",
                    reason="insufficient_points",
                    current_points=current_points,
                    start_at=start_at,
                )
                return {
                    "eligible": 0,
                    "entered": 0,
                    "failed": 0,
                    "points_spent": 0,
                    "skipped": True,
                    "reason": f"insufficient_points ({current_points}P < {start_at}P required)",
                }

            # Get eligible giveaways
            max_entries = settings.max_entries_per_cycle or 10
            eligible = await giveaway_service.get_eligible_giveaways(
                min_price=settings.autojoin_min_price or 0,
                max_price=None,
                min_score=settings.autojoin_min_score,
                min_reviews=settings.autojoin_min_reviews,
                max_game_age=settings.autojoin_max_game_age,
                limit=max_entries,
            )

            stats = {
                "eligible": len(eligible),
                "entered": 0,
                "failed": 0,
                "points_spent": 0,
                "skipped": False,
            }

            if not eligible:
                logger.info("giveaway_processing_completed", **stats)
                await notification_service.log_activity(
                    level="info",
                    event_type="entry",
                    message="Processing completed: No eligible giveaways found"
                )
                return stats

            # Process giveaways with delays
            delay_min = settings.entry_delay_min or 5
            delay_max = settings.entry_delay_max or 15

            for i, giveaway in enumerate(eligible):
                # Check if we should stop (points dropped below stop_at threshold)
                if stop_at > 0:
                    current_points = await giveaway_service.get_current_points()
                    if current_points <= stop_at:
                        logger.info(
                            "giveaway_processing_stopped",
                            reason="points_below_stop_threshold",
                            current_points=current_points,
                            stop_at=stop_at,
                        )
                        await notification_service.log_activity(
                            level="info",
                            event_type="entry",
                            message=f"Processing stopped: points ({current_points}P) dropped to stop threshold ({stop_at}P)"
                        )
                        break

                # Apply delay between entries (except for first one)
                if i > 0:
                    delay = random.uniform(delay_min, delay_max)
                    logger.debug("entry_delay", delay=delay)
                    await asyncio.sleep(delay)

                try:
                    entry = await giveaway_service.enter_giveaway(
                        giveaway.code,
                        entry_type="auto"
                    )

                    if entry:
                        stats["entered"] += 1
                        stats["points_spent"] += entry.points_spent

                        # Log activity
                        await notification_service.log_entry_success(
                            giveaway_code=giveaway.code,
                            game_name=giveaway.game_name,
                            points=entry.points_spent
                        )

                        # Emit entry event
                        await event_manager.broadcast_event(
                            "entry_success",
                            {
                                "giveaway_code": giveaway.code,
                                "game_name": giveaway.game_name,
                                "points_spent": entry.points_spent,
                            }
                        )

                        logger.info(
                            "giveaway_entered",
                            code=giveaway.code,
                            points_spent=entry.points_spent,
                        )
                    else:
                        stats["failed"] += 1

                        # Log activity
                        await notification_service.log_entry_failure(
                            giveaway_code=giveaway.code,
                            game_name=giveaway.game_name,
                            reason="Entry returned none"
                        )

                        logger.warning(
                            "giveaway_entry_failed",
                            code=giveaway.code,
                            reason="entry_returned_none",
                        )

                except Exception as e:
                    stats["failed"] += 1

                    # Log activity
                    await notification_service.log_entry_failure(
                        giveaway_code=giveaway.code,
                        game_name=giveaway.game_name,
                        reason=str(e)
                    )

                    logger.error(
                        "giveaway_entry_error",
                        code=giveaway.code,
                        error=str(e),
                    )

                    # Emit error event
                    await event_manager.broadcast_event(
                        "entry_failed",
                        {
                            "giveaway_code": giveaway.code,
                            "error": str(e),
                        }
                    )

            # Calculate processing time
            end_time = datetime.now(UTC)
            processing_time = (end_time - start_time).total_seconds()
            stats["processing_time"] = round(processing_time, 2)

            # Log completion
            await notification_service.log_activity(
                level="info",
                event_type="entry",
                message=f"Processing completed: {stats['entered']} entered, {stats['failed']} failed, {stats['points_spent']}P spent",
                details=stats
            )

            logger.info(
                "giveaway_processing_completed",
                **stats,
            )

            # Emit completion event
            await event_manager.broadcast_event("processing_completed", stats)

            return stats

        except Exception as e:
            logger.error(
                "giveaway_processing_failed",
                error=str(e),
                error_type=type(e).__name__,
            )

            # Emit error event
            await event_manager.broadcast_event(
                "processing_failed",
                {"error": str(e)}
            )

            raise
        finally:
            # Close clients
            await sg_client.close()
            await steam_client.close()


async def _process_entries(
    giveaway_service: GiveawayService,
    notification_service: NotificationService,
    settings,
) -> Dict[str, Any]:
    """
    Internal entry processing logic.

    Used by both process_giveaways() and automation_cycle().

    Args:
        giveaway_service: GiveawayService instance
        notification_service: NotificationService instance
        settings: Settings object with autojoin configuration

    Returns:
        Dictionary with entry results
    """
    start_time = datetime.now(UTC)

    # Check current points before starting
    start_at = settings.autojoin_start_at or 0
    stop_at = settings.autojoin_stop_at or 0
    current_points = await giveaway_service.get_current_points()

    if start_at > 0 and current_points < start_at:
        logger.info(
            "entry_processing_skipped",
            reason="insufficient_points",
            current_points=current_points,
            start_at=start_at,
        )
        return {
            "eligible": 0,
            "entered": 0,
            "failed": 0,
            "points_spent": 0,
            "skipped": True,
            "reason": f"insufficient_points ({current_points}P < {start_at}P required)",
        }

    # Get eligible giveaways
    max_entries = settings.max_entries_per_cycle or 10
    eligible = await giveaway_service.get_eligible_giveaways(
        min_price=settings.autojoin_min_price or 0,
        max_price=None,
        min_score=settings.autojoin_min_score,
        min_reviews=settings.autojoin_min_reviews,
        max_game_age=settings.autojoin_max_game_age,
        limit=max_entries,
    )

    stats = {
        "eligible": len(eligible),
        "entered": 0,
        "failed": 0,
        "points_spent": 0,
        "skipped": False,
    }

    if not eligible:
        logger.info("no_eligible_giveaways")
        await notification_service.log_activity(
            level="info",
            event_type="entry",
            message="Processing completed: No eligible giveaways found"
        )
        return stats

    # Process giveaways with delays
    delay_min = settings.entry_delay_min or 5
    delay_max = settings.entry_delay_max or 15

    for i, giveaway in enumerate(eligible):
        # Check if we should stop (points dropped below stop_at threshold)
        if stop_at > 0:
            current_points = await giveaway_service.get_current_points()
            if current_points <= stop_at:
                logger.info(
                    "entry_processing_stopped",
                    reason="points_below_stop_threshold",
                    current_points=current_points,
                    stop_at=stop_at,
                )
                await notification_service.log_activity(
                    level="info",
                    event_type="entry",
                    message=f"Processing stopped: points ({current_points}P) dropped to stop threshold ({stop_at}P)"
                )
                break

        # Apply delay between entries (except for first one)
        if i > 0:
            delay = random.uniform(delay_min, delay_max)
            logger.debug("entry_delay", delay=delay)
            await asyncio.sleep(delay)

        try:
            entry = await giveaway_service.enter_giveaway(
                giveaway.code,
                entry_type="auto"
            )

            if entry:
                stats["entered"] += 1
                stats["points_spent"] += entry.points_spent

                # Log activity
                await notification_service.log_entry_success(
                    giveaway_code=giveaway.code,
                    game_name=giveaway.game_name,
                    points=entry.points_spent
                )

                # Emit entry event
                await event_manager.broadcast_event(
                    "entry_success",
                    {
                        "giveaway_code": giveaway.code,
                        "game_name": giveaway.game_name,
                        "points_spent": entry.points_spent,
                    }
                )

                logger.info(
                    "giveaway_entered",
                    code=giveaway.code,
                    points_spent=entry.points_spent,
                )
            else:
                stats["failed"] += 1

                # Log activity
                await notification_service.log_entry_failure(
                    giveaway_code=giveaway.code,
                    game_name=giveaway.game_name,
                    reason="Entry returned none"
                )

                logger.warning(
                    "giveaway_entry_failed",
                    code=giveaway.code,
                    reason="entry_returned_none",
                )

        except Exception as e:
            stats["failed"] += 1

            # Log activity
            await notification_service.log_entry_failure(
                giveaway_code=giveaway.code,
                game_name=giveaway.game_name,
                reason=str(e)
            )

            logger.error(
                "giveaway_entry_error",
                code=giveaway.code,
                error=str(e),
            )

            # Emit error event
            await event_manager.broadcast_event(
                "entry_failed",
                {
                    "giveaway_code": giveaway.code,
                    "error": str(e),
                }
            )

    # Calculate processing time
    end_time = datetime.now(UTC)
    stats["processing_time"] = round((end_time - start_time).total_seconds(), 2)

    # Log completion
    await notification_service.log_activity(
        level="info",
        event_type="entry",
        message=f"Processing completed: {stats['entered']} entered, {stats['failed']} failed, {stats['points_spent']}P spent",
        details=stats
    )

    logger.info("entry_processing_completed", **stats)

    return stats


async def enter_single_giveaway(giveaway_code: str) -> Dict[str, Any]:
    """
    Enter a single giveaway by code.

    Manual entry function for user-initiated entries.

    Args:
        giveaway_code: The giveaway code to enter

    Returns:
        Dictionary with entry result:
            - success: Whether entry was successful
            - points_spent: Points spent on entry
            - error: Error message if failed

    Example:
        >>> result = await enter_single_giveaway("ABC123")
        >>> if result["success"]:
        ...     print(f"Entered! Spent {result['points_spent']} points")
    """
    logger.info("single_entry_started", code=giveaway_code)

    async with AsyncSessionLocal() as session:
        settings_service = SettingsService(session)
        settings = await settings_service.get_settings()

        if not settings.phpsessid:
            return {
                "success": False,
                "points_spent": 0,
                "error": "Not authenticated",
            }

        sg_client = SteamGiftsClient(
            phpsessid=settings.phpsessid,
            user_agent=settings.user_agent,
        )
        await sg_client.start()

        steam_client = SteamClient()
        await steam_client.start()

        # Create services
        game_service = GameService(session=session, steam_client=steam_client)
        giveaway_service = GiveawayService(
            session=session,
            steamgifts_client=sg_client,
            game_service=game_service,
        )
        notification_service = NotificationService(session=session)

        try:
            entry = await giveaway_service.enter_giveaway(
                giveaway_code,
                entry_type="manual"
            )

            if entry:
                logger.info(
                    "single_entry_success",
                    code=giveaway_code,
                    points_spent=entry.points_spent,
                )

                return {
                    "success": True,
                    "points_spent": entry.points_spent,
                    "error": None,
                }
            else:
                return {
                    "success": False,
                    "points_spent": 0,
                    "error": "Entry failed",
                }

        except Exception as e:
            logger.error(
                "single_entry_failed",
                code=giveaway_code,
                error=str(e),
            )

            return {
                "success": False,
                "points_spent": 0,
                "error": str(e),
            }
        finally:
            # Close clients
            await sg_client.close()
            await steam_client.close()
