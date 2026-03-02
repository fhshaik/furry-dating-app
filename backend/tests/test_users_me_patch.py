"""Tests for PATCH /api/users/me endpoint."""

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


def _make_user(
    user_id: int = 1,
    display_name: str = "Test User",
    bio: str | None = None,
    age: int | None = None,
    city: str | None = None,
    nsfw_enabled: bool = False,
    relationship_style: str | None = None,
) -> MagicMock:
    user = MagicMock(spec=User)
    user.id = user_id
    user.oauth_provider = "google"
    user.oauth_id = "oauth-123"
    user.email = "test@example.com"
    user.display_name = display_name
    user.bio = bio
    user.age = age
    user.city = city
    user.nsfw_enabled = nsfw_enabled
    user.relationship_style = relationship_style
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


def test_update_me_unauthenticated_returns_401(client: TestClient):
    """No cookie → 401."""
    response = client.patch("/api/users/me", json={})
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Empty payload (no-op)
# ---------------------------------------------------------------------------


def test_update_me_empty_body_returns_current_user():
    """Empty body → 200 with unchanged user data, no DB write."""
    user = _make_user(user_id=5, display_name="Original Name", bio="My bio")
    mock_session = AsyncMock()

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db(mock_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.patch("/api/users/me", json={})
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert data["display_name"] == "Original Name"
    assert data["bio"] == "My bio"
    mock_session.commit.assert_not_called()


# ---------------------------------------------------------------------------
# Update individual fields
# ---------------------------------------------------------------------------


def test_update_me_display_name():
    """Updating display_name → 200 with new value."""
    user = _make_user(user_id=1, display_name="Old Name")
    mock_session = AsyncMock()

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db(mock_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.patch("/api/users/me", json={"display_name": "New Name"})
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    assert response.json()["display_name"] == "New Name"
    mock_session.commit.assert_called_once()


def test_update_me_trims_strings_and_normalizes_blank_optionals():
    """Whitespace is trimmed and blank optional strings become null."""
    user = _make_user(user_id=12, display_name="Old Name", city="Seattle")
    mock_session = AsyncMock()

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db(mock_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.patch(
                "/api/users/me",
                json={
                    "display_name": "  New Name  ",
                    "city": "   ",
                    "relationship_style": "  polyamorous  ",
                },
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert data["display_name"] == "New Name"
    assert data["city"] is None
    assert data["relationship_style"] == "polyamorous"


def test_update_me_bio():
    """Updating bio → 200 with new bio."""
    user = _make_user(user_id=2)
    mock_session = AsyncMock()

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db(mock_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.patch("/api/users/me", json={"bio": "I love furries"})
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    assert response.json()["bio"] == "I love furries"
    mock_session.commit.assert_called_once()


def test_update_me_multiple_fields():
    """Updating multiple fields at once → all updated."""
    user = _make_user(user_id=3)
    mock_session = AsyncMock()

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db(mock_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.patch(
                "/api/users/me",
                json={"age": 25, "city": "Portland", "relationship_style": "polyamorous"},
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert data["age"] == 25
    assert data["city"] == "Portland"
    assert data["relationship_style"] == "polyamorous"
    mock_session.commit.assert_called_once()


def test_update_me_nsfw_enabled():
    """Enabling nsfw_enabled → 200 with nsfw_enabled=True."""
    user = _make_user(user_id=4, nsfw_enabled=False)
    mock_session = AsyncMock()

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db(mock_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.patch("/api/users/me", json={"nsfw_enabled": True})
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    assert response.json()["nsfw_enabled"] is True


# ---------------------------------------------------------------------------
# Clear nullable fields
# ---------------------------------------------------------------------------


def test_update_me_clear_bio():
    """Setting bio to null → 200 with bio=None."""
    user = _make_user(user_id=6, bio="Existing bio")
    mock_session = AsyncMock()

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db(mock_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.patch("/api/users/me", json={"bio": None})
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    assert response.json()["bio"] is None
    mock_session.commit.assert_called_once()


def test_update_me_clear_city():
    """Setting city to null → 200 with city=None."""
    user = _make_user(user_id=7, city="Portland")
    mock_session = AsyncMock()

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db(mock_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.patch("/api/users/me", json={"city": None})
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    assert response.json()["city"] is None
    mock_session.commit.assert_called_once()


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


def test_update_me_empty_display_name_returns_422():
    """Empty string display_name → 422."""
    user = _make_user(user_id=8)
    mock_session = AsyncMock()

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db(mock_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.patch("/api/users/me", json={"display_name": ""})
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 422


def test_update_me_whitespace_display_name_returns_422():
    """Whitespace-only display_name → 422."""
    user = _make_user(user_id=9)
    mock_session = AsyncMock()

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db(mock_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.patch("/api/users/me", json={"display_name": "   "})
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 422


def test_update_me_null_display_name_returns_422():
    """Explicitly null display_name → 422 (it's a required field)."""
    user = _make_user(user_id=10)
    mock_session = AsyncMock()

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db(mock_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.patch("/api/users/me", json={"display_name": None})
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Response shape
# ---------------------------------------------------------------------------


def test_update_me_response_excludes_oauth_id():
    """Response must not expose oauth_id."""
    user = _make_user(user_id=11)
    mock_session = AsyncMock()

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db(mock_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.patch("/api/users/me", json={"bio": "hello"})
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    assert "oauth_id" not in response.json()
