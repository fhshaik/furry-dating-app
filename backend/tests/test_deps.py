"""Unit tests for get_current_user FastAPI dependency."""

import time
from unittest.mock import AsyncMock, MagicMock

import pytest
from authlib.jose import jwt
from fastapi import HTTPException

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.security import create_access_token
from app.models.user import User


def _make_mock_request(token: str | None) -> MagicMock:
    """Return a mock Request whose cookies map access_token to the given value."""
    request = MagicMock()
    request.cookies.get = MagicMock(return_value=token)
    return request


def _make_mock_db(user: User | None) -> AsyncMock:
    """Return a mock AsyncSession whose .get() resolves to the given user."""
    db = AsyncMock()
    db.get = AsyncMock(return_value=user)
    return db


def _make_user(user_id: int = 1) -> MagicMock:
    user = MagicMock(spec=User)
    user.id = user_id
    return user


# ---------------------------------------------------------------------------
# Missing cookie
# ---------------------------------------------------------------------------


async def test_get_current_user_no_cookie_raises_401():
    """No cookie → 401 Not authenticated."""
    request = _make_mock_request(token=None)
    db = _make_mock_db(user=None)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(request=request, db=db)

    assert exc_info.value.status_code == 401
    assert "authenticated" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# Invalid / malformed token
# ---------------------------------------------------------------------------


async def test_get_current_user_garbage_token_raises_401():
    """A completely invalid token string → 401 Invalid token."""
    request = _make_mock_request(token="not.a.valid.jwt")
    db = _make_mock_db(user=None)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(request=request, db=db)

    assert exc_info.value.status_code == 401
    assert "invalid token" in exc_info.value.detail.lower()


async def test_get_current_user_wrong_secret_raises_401():
    """JWT signed with a wrong secret → 401 Invalid token."""
    claims = {"sub": "1", "iat": int(time.time()), "exp": int(time.time()) + 3600}
    token: bytes = jwt.encode({"alg": "HS256"}, claims, "wrong-secret")
    request = _make_mock_request(token=token.decode("utf-8"))
    db = _make_mock_db(user=None)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(request=request, db=db)

    assert exc_info.value.status_code == 401


async def test_get_current_user_expired_token_raises_401():
    """An expired JWT → 401 Invalid token."""
    claims = {"sub": "1", "iat": int(time.time()) - 7200, "exp": int(time.time()) - 3600}
    token: bytes = jwt.encode({"alg": "HS256"}, claims, settings.jwt_secret)
    request = _make_mock_request(token=token.decode("utf-8"))
    db = _make_mock_db(user=None)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(request=request, db=db)

    assert exc_info.value.status_code == 401
    assert "invalid token" in exc_info.value.detail.lower()


async def test_get_current_user_missing_sub_claim_raises_401():
    """JWT without a 'sub' claim → 401 Invalid token."""
    claims = {"iat": int(time.time()), "exp": int(time.time()) + 3600}
    token: bytes = jwt.encode({"alg": "HS256"}, claims, settings.jwt_secret)
    request = _make_mock_request(token=token.decode("utf-8"))
    db = _make_mock_db(user=None)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(request=request, db=db)

    assert exc_info.value.status_code == 401
    assert "invalid token" in exc_info.value.detail.lower()


async def test_get_current_user_non_integer_sub_raises_401():
    """JWT with a non-integer 'sub' → 401 Invalid token."""
    claims = {"sub": "not-an-int", "iat": int(time.time()), "exp": int(time.time()) + 3600}
    token: bytes = jwt.encode({"alg": "HS256"}, claims, settings.jwt_secret)
    request = _make_mock_request(token=token.decode("utf-8"))
    db = _make_mock_db(user=None)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(request=request, db=db)

    assert exc_info.value.status_code == 401
    assert "invalid token" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# Valid token but user absent from DB
# ---------------------------------------------------------------------------


async def test_get_current_user_user_not_found_raises_401():
    """Valid JWT but user deleted from DB → 401 User not found."""
    token = create_access_token(user_id=999)
    request = _make_mock_request(token=token)
    db = _make_mock_db(user=None)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(request=request, db=db)

    assert exc_info.value.status_code == 401
    assert "not found" in exc_info.value.detail.lower()
    db.get.assert_awaited_once_with(User, 999)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


async def test_get_current_user_returns_user():
    """Valid JWT + user exists in DB → the User object is returned."""
    user = _make_user(user_id=42)
    token = create_access_token(user_id=42)
    request = _make_mock_request(token=token)
    db = _make_mock_db(user=user)

    result = await get_current_user(request=request, db=db)

    assert result is user
    db.get.assert_awaited_once_with(User, 42)


async def test_get_current_user_queries_correct_user_id():
    """The user_id extracted from the JWT is used to query the database."""
    user = _make_user(user_id=7)
    token = create_access_token(user_id=7)
    request = _make_mock_request(token=token)
    db = _make_mock_db(user=user)

    await get_current_user(request=request, db=db)

    db.get.assert_awaited_once_with(User, 7)
