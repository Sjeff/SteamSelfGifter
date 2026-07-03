"""Session model for server-side login sessions.

Sessions are stored in the database (not signed JWTs) so they survive a
container restart and can be revoked server-side on logout. Only a hash
of the session token is persisted, mirroring how credentials are never
stored in plaintext elsewhere in the app.
"""

from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TZDateTime


class AuthSession(Base):
    """A logged-in session tied to a single user."""

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(
        String,
        nullable=False,
        unique=True,
        comment="SHA-256 hash of the session token stored in the cookie",
    )
    expires_at: Mapped[datetime] = mapped_column(
        TZDateTime,
        nullable=False,
        comment="Session is invalid after this time, regardless of cookie lifetime",
    )
    created_at: Mapped[datetime] = mapped_column(
        TZDateTime,
        nullable=False,
        comment="When the session was created",
    )

    def __repr__(self) -> str:
        return f"<AuthSession(id={self.id}, user_id={self.user_id})>"
