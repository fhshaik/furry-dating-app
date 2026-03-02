"""Google and Discord OAuth 2.0 redirect and callback endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.oauth import (
    DISCORD_AUTHORIZE_URL,
    DISCORD_TOKEN_URL,
    DISCORD_USERINFO_URL,
    GOOGLE_AUTHORIZE_URL,
    GOOGLE_TOKEN_URL,
    GOOGLE_USERINFO_URL,
    create_discord_client,
    create_google_client,
)
from app.core.security import create_access_token
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserMeResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

_COOKIE_NAME = "access_token"
_COOKIE_MAX_AGE = 60 * 60 * 24 * 7  # 7 days


def _build_redirect_uri(provider: str) -> str:
    return f"{settings.backend_url.rstrip('/')}/api/auth/{provider}/callback"


@router.get("/demo")
async def demo_login(request: Request, db: AsyncSession = Depends(get_db)) -> RedirectResponse:
    """Log in as the first seed user (development only). Use to explore example data."""
    if settings.environment != "development":
        raise HTTPException(status_code=404, detail="Not found")
    result = await db.execute(
        select(User).where(User.oauth_id.like("seed-%")).order_by(User.id).limit(1)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="No demo user found. Use a fresh database so the example data seed runs.",
        )
    access_token = create_access_token(user.id)
    response = RedirectResponse(url=f"{settings.frontend_url}/auth/callback")
    response.set_cookie(
        key=_COOKIE_NAME,
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=_COOKIE_MAX_AGE,
    )
    return response


@router.get("/google")
async def google_login(request: Request) -> RedirectResponse:
    """Redirect the browser to Google's OAuth consent screen."""
    redirect_uri = _build_redirect_uri("google")
    client = create_google_client(redirect_uri=redirect_uri)
    uri, state = client.create_authorization_url(GOOGLE_AUTHORIZE_URL)
    request.session["oauth_state"] = state
    return RedirectResponse(uri)


@router.get("/google/callback")
async def google_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Handle Google's redirect, exchange code for tokens, upsert user, set cookie."""
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    stored_state = request.session.pop("oauth_state", None)

    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")
    if state != stored_state:
        raise HTTPException(status_code=400, detail="OAuth state mismatch")

    redirect_uri = _build_redirect_uri("google")
    client = create_google_client(redirect_uri=redirect_uri)

    try:
        await client.fetch_token(
            GOOGLE_TOKEN_URL,
            code=code,
            redirect_uri=redirect_uri,
        )
    except Exception as exc:
        logger.warning("Google token exchange failed: %s", exc)
        raise HTTPException(status_code=400, detail="Token exchange failed") from exc

    try:
        resp = await client.get(GOOGLE_USERINFO_URL)
        resp.raise_for_status()
        userinfo: dict = resp.json()
    except Exception as exc:
        logger.warning("Google userinfo fetch failed: %s", exc)
        raise HTTPException(status_code=400, detail="Failed to fetch user info") from exc

    google_id: str = userinfo["sub"]
    email: str | None = userinfo.get("email")
    display_name: str = userinfo.get("name") or email or google_id

    result = await db.execute(
        select(User).where(User.oauth_provider == "google", User.oauth_id == google_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            oauth_provider="google",
            oauth_id=google_id,
            email=email,
            display_name=display_name,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    elif user.email != email or user.display_name != display_name:
        user.email = email
        user.display_name = display_name
        await db.commit()

    access_token = create_access_token(user.id)

    response = RedirectResponse(url=f"{settings.frontend_url}/auth/callback")
    response.set_cookie(
        key=_COOKIE_NAME,
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=settings.environment != "development",
        max_age=_COOKIE_MAX_AGE,
    )
    return response


# ---------------------------------------------------------------------------
# Discord OAuth
# ---------------------------------------------------------------------------
@router.get("/discord")
async def discord_login(request: Request) -> RedirectResponse:
    """Redirect the browser to Discord's OAuth consent screen."""
    redirect_uri = _build_redirect_uri("discord")
    client = create_discord_client(redirect_uri=redirect_uri)
    uri, state = client.create_authorization_url(DISCORD_AUTHORIZE_URL)
    request.session["oauth_state"] = state
    return RedirectResponse(uri)


@router.get("/discord/callback")
async def discord_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Handle Discord's redirect, exchange code for tokens, upsert user, set cookie."""
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    stored_state = request.session.pop("oauth_state", None)

    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")
    if state != stored_state:
        raise HTTPException(status_code=400, detail="OAuth state mismatch")

    redirect_uri = _build_redirect_uri("discord")
    client = create_discord_client(redirect_uri=redirect_uri)

    try:
        await client.fetch_token(
            DISCORD_TOKEN_URL,
            code=code,
            redirect_uri=redirect_uri,
        )
    except Exception as exc:
        logger.warning("Discord token exchange failed: %s", exc)
        raise HTTPException(status_code=400, detail="Token exchange failed") from exc

    try:
        resp = await client.get(DISCORD_USERINFO_URL)
        resp.raise_for_status()
        userinfo: dict = resp.json()
    except Exception as exc:
        logger.warning("Discord userinfo fetch failed: %s", exc)
        raise HTTPException(status_code=400, detail="Failed to fetch user info") from exc

    discord_id: str = userinfo["id"]
    email: str | None = userinfo.get("email")
    username: str = userinfo.get("username") or discord_id
    display_name: str = email or username

    result = await db.execute(
        select(User).where(User.oauth_provider == "discord", User.oauth_id == discord_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            oauth_provider="discord",
            oauth_id=discord_id,
            email=email,
            display_name=display_name,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    elif user.email != email or user.display_name != display_name:
        user.email = email
        user.display_name = display_name
        await db.commit()

    access_token = create_access_token(user.id)

    response = RedirectResponse(url=f"{settings.frontend_url}/auth/callback")
    response.set_cookie(
        key=_COOKIE_NAME,
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=settings.environment != "development",
        max_age=_COOKIE_MAX_AGE,
    )
    return response

# ---------------------------------------------------------------------------
# Current user
# ---------------------------------------------------------------------------


@router.get("/me", response_model=UserMeResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    """Return the currently authenticated user's profile."""
    return current_user


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------


@router.post("/logout")
async def logout() -> JSONResponse:
    """Clear the access_token cookie, ending the session."""
    response = JSONResponse(content={"message": "Logged out"})
    response.delete_cookie(
        key=_COOKIE_NAME,
        httponly=True,
        samesite="lax",
        secure=settings.environment != "development",
    )
    return response
