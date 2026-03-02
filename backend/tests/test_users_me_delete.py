"""Tests for DELETE /api/users/me endpoint."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.deps import get_current_user
from app.database import get_db
from app.main import app
from app.models.user import User


@pytest.fixture()
def client():
    with TestClient(app, follow_redirects=False) as c:
        yield c


def _make_user(user_id: int = 1) -> MagicMock:
    user = MagicMock(spec=User)
    user.id = user_id
    user.oauth_provider = "google"
    user.oauth_id = "oauth-123"
    user.email = "test@example.com"
    user.display_name = "Test User"
    user.bio = None
    user.age = None
    user.city = None
    user.nsfw_enabled = False
    user.relationship_style = None
    user.created_at = datetime(2025, 1, 1, 0, 0, 0)
    return user


def _override_current_user(user: MagicMock):
    async def _override():
        return user

    return _override


def _override_db(mock_session: AsyncMock):
    async def _db():
        yield mock_session

    return _db


# ---------------------------------------------------------------------------
# Unauthenticated
# ---------------------------------------------------------------------------


def test_delete_me_unauthenticated_returns_401(client: TestClient):
    """No cookie → 401."""
    response = client.delete("/api/users/me")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Successful deletion
# ---------------------------------------------------------------------------


def test_delete_me_returns_204():
    """Authenticated request → 204 with empty body."""
    user = _make_user(user_id=1)
    mock_session = AsyncMock()

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db(mock_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.delete("/api/users/me")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 204
    assert response.content == b""


def test_delete_me_calls_db_delete_and_commit():
    """Deletion calls db.delete(user) and db.commit()."""
    user = _make_user(user_id=2)
    mock_session = AsyncMock()

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db(mock_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            c.delete("/api/users/me")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    mock_session.delete.assert_called_once_with(user)
    mock_session.commit.assert_called_once()


def test_delete_me_clears_access_token_cookie():
    """Response clears the access_token cookie."""
    user = _make_user(user_id=3)
    mock_session = AsyncMock()

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db(mock_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.delete("/api/users/me")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 204
    # The Set-Cookie header should clear (delete) the access_token cookie
    set_cookie = response.headers.get("set-cookie", "")
    assert "access_token" in set_cookie
