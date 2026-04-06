"""Account model for multi-account SteamGifts support."""

from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin, TZDateTime


class Account(Base, TimestampMixin):
    """
    SteamGifts account with credentials and per-account automation settings.

    Replaces the singleton Settings model for credential storage.
    Multiple accounts can exist; one is marked as the default for
    backward-compatible API access.

    Attributes:
        id: Auto-increment primary key
        name: Display name for the account (e.g. "Main", "Alt")
        is_active: Whether this account is active
        is_default: Whether this is the default/legacy account

        SteamGifts Authentication:
            phpsessid: SteamGifts session cookie
            user_agent: Browser user agent string
            xsrf_token: Anti-CSRF token (extracted from pages, cached)

        Automation Config (same fields as Settings model):
            All autojoin, scheduler, and advanced settings per-account.
    """

    __tablename__ = "accounts"

    # ==================== Identity ====================
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    name: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="Default",
        comment="Display name for this account",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether this account is active",
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether this is the default/legacy account",
    )

    # ==================== SteamGifts Authentication ====================
    phpsessid: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        comment="SteamGifts session cookie for authentication",
    )
    user_agent: Mapped[str] = mapped_column(
        String,
        default="Mozilla/5.0 (X11; Fedora; Linux x86_64; rv:82.0) Gecko/20100101 Firefox/82.0",
        comment="Browser user agent for HTTP requests",
    )
    xsrf_token: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        comment="Anti-CSRF token from SteamGifts",
    )

    # ==================== DLC Settings ====================
    dlc_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Whether to enter DLC giveaways",
    )

    # ==================== Safety Settings ====================
    safety_check_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="Check giveaways for traps before auto-entering",
    )
    auto_hide_unsafe: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="Automatically hide unsafe giveaways on SteamGifts",
    )

    # ==================== Auto-join Settings ====================
    autojoin_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Enable automatic giveaway entry",
    )
    autojoin_start_at: Mapped[int] = mapped_column(
        Integer,
        default=350,
        comment="Start entering when points >= this value",
    )
    autojoin_stop_at: Mapped[int] = mapped_column(
        Integer,
        default=200,
        comment="Stop entering when points <= this value",
    )
    autojoin_min_price: Mapped[int] = mapped_column(
        Integer,
        default=10,
        comment="Minimum giveaway price in points",
    )
    autojoin_min_score: Mapped[int] = mapped_column(
        Integer,
        default=7,
        comment="Minimum Steam review score (0-10)",
    )
    autojoin_min_reviews: Mapped[int] = mapped_column(
        Integer,
        default=1000,
        comment="Minimum number of reviews required",
    )
    autojoin_max_game_age: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        default=None,
        comment="Maximum game age in years (None = no limit)",
    )

    # ==================== Scheduler Settings ====================
    scan_interval_minutes: Mapped[int] = mapped_column(
        Integer,
        default=30,
        comment="Scan interval in minutes",
    )
    max_entries_per_cycle: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Maximum entries per cycle (None = unlimited)",
    )
    automation_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Master switch for automation",
    )

    # ==================== Advanced Settings ====================
    max_scan_pages: Mapped[int] = mapped_column(
        Integer,
        default=3,
        comment="Maximum SteamGifts pages to scan",
    )
    entry_delay_min: Mapped[int] = mapped_column(
        Integer,
        default=8,
        comment="Minimum delay between entries (seconds)",
    )
    entry_delay_max: Mapped[int] = mapped_column(
        Integer,
        default=12,
        comment="Maximum delay between entries (seconds)",
    )

    # ==================== Metadata ====================
    last_synced_at: Mapped[datetime | None] = mapped_column(
        TZDateTime,
        nullable=True,
        comment="Last sync with SteamGifts",
    )

    def __repr__(self) -> str:
        return f"<Account(id={self.id}, name='{self.name}', default={self.is_default})>"
