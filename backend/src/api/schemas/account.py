"""API schemas for accounts endpoints."""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class AccountBase(BaseModel):
    """Base account schema with automation config fields."""

    name: str = Field(default="Default", description="Display name for this account")

    # Credentials
    phpsessid: Optional[str] = Field(default=None, description="SteamGifts session cookie")
    user_agent: str = Field(
        default="Mozilla/5.0 (X11; Fedora; Linux x86_64; rv:82.0) Gecko/20100101 Firefox/82.0",
        description="Browser user agent string",
    )
    xsrf_token: Optional[str] = Field(default=None, description="Anti-CSRF token (auto-managed)")

    # DLC
    dlc_enabled: bool = Field(default=False, description="Whether to enter DLC giveaways")

    # Safety
    safety_check_enabled: bool = Field(default=True, description="Check giveaways for traps")
    auto_hide_unsafe: bool = Field(default=True, description="Automatically hide unsafe giveaways")

    # Autojoin
    autojoin_enabled: bool = Field(default=False, description="Enable automatic giveaway entry")
    autojoin_start_at: int = Field(default=350, ge=0, description="Start entering when points >= this")
    autojoin_stop_at: int = Field(default=200, ge=0, description="Stop entering when points <= this")
    autojoin_min_price: int = Field(default=10, ge=0, description="Minimum giveaway price in points")
    autojoin_min_score: int = Field(default=7, ge=0, le=10, description="Minimum Steam review score (0-10)")
    autojoin_min_reviews: int = Field(default=1000, ge=0, description="Minimum number of reviews")
    autojoin_max_game_age: Optional[int] = Field(default=None, ge=1, description="Max game age in years")

    # Scheduler
    scan_interval_minutes: int = Field(default=30, ge=1, description="Scan interval in minutes")
    max_entries_per_cycle: Optional[int] = Field(default=None, ge=1, description="Max entries per cycle")
    automation_enabled: bool = Field(default=False, description="Master switch for automation")

    # Advanced
    max_scan_pages: int = Field(default=3, ge=1, description="Max pages to scan per cycle")
    entry_delay_min: int = Field(default=8, ge=0, description="Min delay between entries (seconds)")
    entry_delay_max: int = Field(default=12, ge=0, description="Max delay between entries (seconds)")

    @field_validator("entry_delay_max")
    @classmethod
    def validate_delay_range(cls, v, info):
        if "entry_delay_min" in info.data and v < info.data["entry_delay_min"]:
            raise ValueError("entry_delay_max must be >= entry_delay_min")
        return v


class AccountCreate(BaseModel):
    """Schema for creating a new account."""

    name: str = Field(..., min_length=1, description="Display name for this account")
    phpsessid: Optional[str] = Field(default=None, description="SteamGifts session cookie")
    user_agent: Optional[str] = Field(default=None, description="Browser user agent string")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Account name cannot be empty")
        return v.strip()


class AccountUpdate(BaseModel):
    """Schema for updating an account. All fields optional."""

    name: Optional[str] = Field(default=None, description="Display name")
    phpsessid: Optional[str] = Field(default=None, description="SteamGifts session cookie")
    user_agent: Optional[str] = Field(default=None, description="Browser user agent string")
    xsrf_token: Optional[str] = Field(default=None, description="Anti-CSRF token")
    dlc_enabled: Optional[bool] = None
    safety_check_enabled: Optional[bool] = None
    auto_hide_unsafe: Optional[bool] = None
    autojoin_enabled: Optional[bool] = None
    autojoin_start_at: Optional[int] = Field(default=None, ge=0)
    autojoin_stop_at: Optional[int] = Field(default=None, ge=0)
    autojoin_min_price: Optional[int] = Field(default=None, ge=0)
    autojoin_min_score: Optional[int] = Field(default=None, ge=0, le=10)
    autojoin_min_reviews: Optional[int] = Field(default=None, ge=0)
    autojoin_max_game_age: Optional[int] = Field(default=None, ge=1)
    scan_interval_minutes: Optional[int] = Field(default=None, ge=1)
    max_entries_per_cycle: Optional[int] = Field(default=None, ge=1)
    automation_enabled: Optional[bool] = None
    max_scan_pages: Optional[int] = Field(default=None, ge=1)
    entry_delay_min: Optional[int] = Field(default=None, ge=0)
    entry_delay_max: Optional[int] = Field(default=None, ge=0)


class AccountResponse(AccountBase):
    """Full account response schema."""

    id: int
    is_active: bool
    is_default: bool
    last_synced_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AccountListItem(BaseModel):
    """Lightweight account for list endpoints."""

    id: int
    name: str
    is_active: bool
    is_default: bool
    automation_enabled: bool
    autojoin_enabled: bool
    has_credentials: bool = False

    model_config = {"from_attributes": True}

    @classmethod
    def model_validate(cls, obj, *args, **kwargs):
        # Map phpsessid presence to has_credentials
        if hasattr(obj, "phpsessid"):
            data = {
                "id": obj.id,
                "name": obj.name,
                "is_active": obj.is_active,
                "is_default": obj.is_default,
                "automation_enabled": obj.automation_enabled,
                "autojoin_enabled": obj.autojoin_enabled,
                "has_credentials": bool(obj.phpsessid),
            }
            return cls(**data)
        return super().model_validate(obj, *args, **kwargs)


class AccountCredentials(BaseModel):
    """Schema for setting credentials."""

    phpsessid: str = Field(..., min_length=1, description="SteamGifts PHPSESSID cookie")
    user_agent: Optional[str] = Field(default=None, description="Browser user agent string")

    @field_validator("phpsessid")
    @classmethod
    def validate_phpsessid(cls, v):
        if not v or not v.strip():
            raise ValueError("phpsessid cannot be empty")
        return v.strip()
