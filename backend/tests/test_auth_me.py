"""Tests for GET /api/auth/me endpoint."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.main import app
from app.models.user import User


@pytest.fixture()
def client():
    with TestClient(app, follow_redirects=False) as c:
        yield c


def _make_user(
    user_id: int = 1,
    oauth_provider: str = "google",
    email: str = "test@example.com",
    display_name: str = "Test User",
) -> MagicMock:
    user = MagicMock(spec=User)
    user.id = user_id
    user.oauth_provider = oauth_provider
    user.oauth_id = "oauth-123"
    user.email = email
    user.display_name = display_name
    user.bio = None
    user.age = None
    user.city = None
    user.nsfw_enabled = False
    user.relationship_style = None
    user.created_at = datetime(2025, 1, 1, 0, 0, 0)
    return user


# ---------------------------------------------------------------------------
# GET /api/auth/me — unauthenticated
# ---------------------------------------------------------------------------


def test_me_no_cookie_returns_401(client: TestClient):
    """Request without cookie must return 401."""
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert "authenticated" in response.json()["detail"].lower()


def test_me_invalid_token_returns_401(client: TestClient):
    """Request with a garbage token must return 401."""
    client.cookies.set("access_token", "not.a.valid.jwt")
    response = client.get("/api/auth/me")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/auth/me — authenticated
# ---------------------------------------------------------------------------


def test_me_returns_current_user():
    """Valid JWT cookie → 200 with the authenticated user's data."""
    from app.core.deps import get_current_user
    from app.main import app as _app

    user = _make_user(user_id=42)

    async def _override():
        return user

    _app.dependency_overrides[get_current_user] = _override
    try:
        with TestClient(_app, follow_redirects=False) as c:
            response = c.get("/api/auth/me")
    finally:
        _app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 42
    assert data["email"] == "test@example.com"
    assert data["display_name"] == "Test User"
    assert data["oauth_provider"] == "google"
    assert data["nsfw_enabled"] is False
    assert data["bio"] is None


def test_me_with_real_jwt_and_mock_db():
    """End-to-end: real JWT in cookie, mock DB returning user → 200."""
    from app.database import get_db
    from app.main import app as _app

    user = _make_user(user_id=7)

    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.get = AsyncMock(return_value=user)

    async def _db_override():
        yield mock_session

    _app.dependency_overrides[get_db] = _db_override
    try:
        token = create_access_token(user_id=7)
        with TestClient(_app, follow_redirects=False) as c:
            c.cookies.set("access_token", token)
            response = c.get("/api/auth/me")
    finally:
        _app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 7
    assert data["display_name"] == "Test User"


def test_me_user_not_found_in_db_returns_401():
    """Valid JWT but user deleted from DB → 401."""
    from app.database import get_db
    from app.main import app as _app

    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.get = AsyncMock(return_value=None)

    async def _db_override():
        yield mock_session

    _app.dependency_overrides[get_db] = _db_override
    try:
        token = create_access_token(user_id=999)
        with TestClient(_app, follow_redirects=False) as c:
            c.cookies.set("access_token", token)
            response = c.get("/api/auth/me")
    finally:
        _app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 401
    assert "not found" in response.json()["detail"].lower()


def test_me_response_excludes_oauth_id():
    """The /me response must not expose oauth_id."""
    from app.core.deps import get_current_user
    from app.main import app as _app

    user = _make_user(user_id=1)

    async def _override():
        return user

    _app.dependency_overrides[get_current_user] = _override
    try:
        with TestClient(_app, follow_redirects=False) as c:
            response = c.get("/api/auth/me")
    finally:
        _app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    assert "oauth_id" not in response.json()
