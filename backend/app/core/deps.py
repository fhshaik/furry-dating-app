"""FastAPI dependency functions for common request handling."""

from authlib.jose.errors import JoseError
from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.database import get_db
from app.models.user import User

_COOKIE_NAME = "access_token"
_NSFW_MIN_AGE = 18


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate the JWT from the httpOnly cookie, return the User."""
    token = request.cookies.get(_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        claims = decode_access_token(token)
        user_id = int(claims["sub"])
    except (JoseError, KeyError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc

    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return user


async def require_nsfw_access(
    user: User = Depends(get_current_user),
) -> User:
    """Require that the user has confirmed their age and enabled NSFW content.

    Raises 403 if:
    - age is not set (not confirmed)
    - age is below the minimum required age
    - nsfw_enabled is False
    """
    if user.age is None:
        raise HTTPException(status_code=403, detail="Age not confirmed")
    if user.age < _NSFW_MIN_AGE:
        raise HTTPException(
            status_code=403,
            detail=f"Must be {_NSFW_MIN_AGE} or older to access NSFW content",
        )
    if not user.nsfw_enabled:
        raise HTTPException(status_code=403, detail="NSFW content not enabled")
    return user
