"""User model for app-level authentication.

The app supports a single admin account, created once via the frontend
setup wizard. Modeled as a table (rather than a single settings row) to
follow the existing one-repository-per-model convention.
"""

from datetime import datetime

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin, TZDateTime


class User(Base, TimestampMixin):
    """Admin user account used to gate access to the dashboard."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    username: Mapped[str] = mapped_column(
        String,
        nullable=False,
        unique=True,
        comment="Login username",
    )
    password_hash: Mapped[str] = mapped_column(
        String,
        nullable=False,
        comment="bcrypt hash of the password, never the raw value",
    )
    failed_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Consecutive failed login attempts since the last success",
    )
    locked_until: Mapped[datetime | None] = mapped_column(
        TZDateTime,
        nullable=True,
        comment="Login is rejected until this time when set",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}')>"
