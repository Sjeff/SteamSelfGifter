"""Repository for ActivityLog model."""

from typing import Optional
from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.activity_log import ActivityLog


class ActivityLogRepository:
    """
    Repository for ActivityLog data access.

    This repository provides methods for creating and retrieving activity logs.

    Design Notes:
        - Logs are immutable (insert-only, no updates)
        - All queries ordered by created_at desc (newest first)
        - No delete method (logs kept for audit trail)
        - All methods are async

    Usage:
        >>> repo = ActivityLogRepository(session)
        >>> log = await repo.create(level="info", event_type="scan", message="Started scan")
    """

    def __init__(self, session: AsyncSession, account_id: Optional[int] = None):
        """
        Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
            account_id: When set, queries and creates are scoped to this account.
        """
        self.session = session
        self.account_id = account_id

    async def create(
        self,
        level: str,
        event_type: str,
        message: str,
        details: Optional[str] = None,
    ) -> ActivityLog:
        """
        Create a new activity log entry.

        Args:
            level: Log severity ("info", "warning", "error")
            event_type: Event category ("scan", "entry", "error", "config", etc.)
            message: Human-readable log message
            details: Optional JSON-formatted details

        Returns:
            Created ActivityLog object

        Example:
            >>> log = await repo.create(
            ...     level="info",
            ...     event_type="scan",
            ...     message="Found 15 new giveaways",
            ...     details='{"count": 15}'
            ... )
        """
        log = ActivityLog(
            level=level,
            event_type=event_type,
            message=message,
            details=details,
            account_id=self.account_id,
        )
        self.session.add(log)
        await self.session.flush()
        return log

    async def get_by_id(self, log_id: int) -> Optional[ActivityLog]:
        """
        Get activity log by ID.

        Args:
            log_id: Log ID

        Returns:
            ActivityLog object if found, None otherwise

        Example:
            >>> log = await repo.get_by_id(123)
        """
        result = await self.session.execute(
            select(ActivityLog).where(ActivityLog.id == log_id)
        )
        return result.scalar_one_or_none()

    def _account_conditions(self, extra=None):
        """Build WHERE conditions including optional account filter."""
        conditions = list(extra or [])
        if self.account_id is not None:
            conditions.append(ActivityLog.account_id == self.account_id)
        return conditions

    async def get_recent(self, limit: int = 100) -> list[ActivityLog]:
        """Get recent activity logs (scoped to account if set)."""
        conditions = self._account_conditions()
        query = select(ActivityLog)
        if conditions:
            query = query.where(and_(*conditions))
        query = query.order_by(desc(ActivityLog.created_at)).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_level(self, level: str, limit: int = 100) -> list[ActivityLog]:
        """Get activity logs by severity level (scoped to account if set)."""
        conditions = self._account_conditions([ActivityLog.level == level])
        result = await self.session.execute(
            select(ActivityLog)
            .where(and_(*conditions))
            .order_by(desc(ActivityLog.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_event_type(
        self, event_type: str, limit: int = 100
    ) -> list[ActivityLog]:
        """Get activity logs by event type (scoped to account if set)."""
        conditions = self._account_conditions([ActivityLog.event_type == event_type])
        result = await self.session.execute(
            select(ActivityLog)
            .where(and_(*conditions))
            .order_by(desc(ActivityLog.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_by_level(self, level: str) -> int:
        """Count activity logs by severity level (scoped to account if set)."""
        conditions = self._account_conditions([ActivityLog.level == level])
        result = await self.session.execute(
            select(ActivityLog).where(and_(*conditions))
        )
        return len(list(result.scalars().all()))

    async def get_all(self) -> list[ActivityLog]:
        """Get all activity logs (scoped to account if set)."""
        conditions = self._account_conditions()
        query = select(ActivityLog)
        if conditions:
            query = query.where(and_(*conditions))
        query = query.order_by(desc(ActivityLog.created_at))
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def delete_all(self) -> int:
        """
        Delete all activity logs.

        Returns:
            Number of logs deleted

        Example:
            >>> deleted_count = await repo.delete_all()
        """
        from sqlalchemy import delete
        result = await self.session.execute(delete(ActivityLog))
        await self.session.commit()
        return result.rowcount

    async def count(self) -> int:
        """
        Count total activity logs.

        Returns:
            Total count of logs

        Example:
            >>> total = await repo.count()
        """
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.count()).select_from(ActivityLog)
        )
        return result.scalar() or 0
