"""Auth API router: one-time admin setup, login/logout, and current user."""

import structlog
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

logger = structlog.get_logger()

router = APIRouter()


def _set_session_cookie(request: Request, response: Response, token: str) -> None:
    if settings.session_cookie_secure and request.url.scheme != "https":
        # A Secure cookie is silently dropped by the browser on a plain-HTTP
        # origin, so the login response looks successful but no session
        # actually persists. Surface this in the logs instead of leaving
        # users to debug "logged in, but every request is unauthenticated".
        logger.warning(
            "insecure_session_cookie_over_http",
            message=(
                "SESSION_COOKIE_SECURE is true but this request came in over "
                "plain HTTP - the browser will discard the session cookie. "
                "Set SESSION_COOKIE_SECURE=false if not running behind HTTPS."
            ),
        )
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
async def setup(
    body: SetupRequest, request: Request, response: Response, auth_service: AuthServiceDep
):
    """Create the one admin account. Fails if setup was already completed."""
    user = await auth_service.create_admin(body.username, body.password)
    token = await auth_service.create_session(user.id)
    _set_session_cookie(request, response, token)
    return create_success_response(data=UserResponse.model_validate(user))


@router.post("/login", response_model=dict)
async def login(
    body: LoginRequest, request: Request, response: Response, auth_service: AuthServiceDep
):
    """Log in with username and password, setting the session cookie."""
    user = await auth_service.authenticate(body.username, body.password)
    token = await auth_service.create_session(user.id)
    _set_session_cookie(request, response, token)
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
