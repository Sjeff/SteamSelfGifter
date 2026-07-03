"""API schemas for auth endpoints."""

from pydantic import BaseModel, Field, field_validator


class AuthStatus(BaseModel):
    """Whether the one-time admin setup has been completed."""

    setup_complete: bool


class SetupRequest(BaseModel):
    """Schema for creating the one admin account."""

    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=8, max_length=256)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        if not v.strip():
            raise ValueError("Username cannot be empty")
        return v.strip()


class LoginRequest(BaseModel):
    """Schema for logging in."""

    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class ChangePasswordRequest(BaseModel):
    """Schema for changing the current user's password."""

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=256)


class UserResponse(BaseModel):
    """The currently authenticated user."""

    id: int
    username: str

    model_config = {"from_attributes": True}
