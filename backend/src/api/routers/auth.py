"""Auth API router: one-time admin setup, login/logout, and current user."""

from fastapi import APIRouter, Request, Response

from api.dependencies import SESSION_COOKIE_NAME, AuthServiceDep, CurrentUserDep
from api.schemas.auth import (
    AuthStatus,
    ChangePasswordRequest,
    LoginRequest,
    SetupRequest,
    UserResponse,
)
from api.schemas.common import create_success_response
from core.config import settings

router = APIRouter()


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
        # No max_age/expires: browser-session cookie, cleared on browser close.
        # The session is still capped server-side (session_lifetime_hours).
    )


@router.get("/status", response_model=dict)
async def get_status(auth_service: AuthServiceDep):
    """Whether the one-time admin setup has been completed."""
    setup_complete = await auth_service.is_setup_complete()
    return create_success_response(data=AuthStatus(setup_complete=setup_complete))


@router.post("/setup", response_model=dict)
async def setup(body: SetupRequest, response: Response, auth_service: AuthServiceDep):
    """Create the one admin account. Fails if setup was already completed."""
    user = await auth_service.create_admin(body.username, body.password)
    token = await auth_service.create_session(user.id)
    _set_session_cookie(response, token)
    return create_success_response(data=UserResponse.model_validate(user))


@router.post("/login", response_model=dict)
async def login(body: LoginRequest, response: Response, auth_service: AuthServiceDep):
    """Log in with username and password, setting the session cookie."""
    user = await auth_service.authenticate(body.username, body.password)
    token = await auth_service.create_session(user.id)
    _set_session_cookie(response, token)
    return create_success_response(data=UserResponse.model_validate(user))


@router.post("/logout", response_model=dict)
async def logout(request: Request, response: Response, auth_service: AuthServiceDep):
    """Log out: invalidate the session server-side and clear the cookie."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        await auth_service.invalidate_session(token)
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return create_success_response(data={"logged_out": True})


@router.get("/me", response_model=dict)
async def get_me(current_user: CurrentUserDep):
    """The currently authenticated user."""
    return create_success_response(data=UserResponse.model_validate(current_user))


@router.post("/change-password", response_model=dict)
async def change_password(
    body: ChangePasswordRequest, current_user: CurrentUserDep, auth_service: AuthServiceDep
):
    """Change the current user's password."""
    await auth_service.change_password(current_user, body.current_password, body.new_password)
    return create_success_response(data={"changed": True})
