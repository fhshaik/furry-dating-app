"""Tests for GET /api/users/{user_id} public profile endpoint."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

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
    user.oauth_id = "oauth-secret-123"
    user.email = "private@example.com"
    user.display_name = display_name
    user.bio = bio
    user.age = age
    user.city = city
    user.nsfw_enabled = nsfw_enabled
    user.relationship_style = relationship_style
    user.created_at = datetime(2025, 1, 1, 0, 0, 0)
    return user


def _override_db_returning(user: MagicMock | None):
    mock_session = AsyncMock()
    mock_session.get.return_value = user

    async def _db():
        yield mock_session

    return _db


# ---------------------------------------------------------------------------
# 404 — user not found
# ---------------------------------------------------------------------------


def test_get_user_profile_not_found(client: TestClient):
    """Unknown user ID → 404."""
    app.dependency_overrides[get_db] = _override_db_returning(None)
    try:
        response = client.get("/api/users/999")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


# ---------------------------------------------------------------------------
# 200 — found
# ---------------------------------------------------------------------------


def test_get_user_profile_returns_200():
    """Known user ID → 200 with public profile."""
    user = _make_user(user_id=42, display_name="Foxy", bio="Hello!", age=25, city="Seattle")

    app.dependency_overrides[get_db] = _override_db_returning(user)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.get("/api/users/42")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 42
    assert data["display_name"] == "Foxy"
    assert data["bio"] == "Hello!"
    assert data["age"] == 25
    assert data["city"] == "Seattle"


def test_get_user_profile_nullable_fields_none():
    """User with no optional fields → nulls returned."""
    user = _make_user(user_id=7)

    app.dependency_overrides[get_db] = _override_db_returning(user)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.get("/api/users/7")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert data["bio"] is None
    assert data["age"] is None
    assert data["city"] is None
    assert data["relationship_style"] is None


def test_get_user_profile_with_relationship_style():
    """User with relationship_style set → returned in response."""
    user = _make_user(user_id=3, relationship_style="polyamorous")

    app.dependency_overrides[get_db] = _override_db_returning(user)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.get("/api/users/3")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    assert response.json()["relationship_style"] == "polyamorous"


# ---------------------------------------------------------------------------
# Private fields excluded
# ---------------------------------------------------------------------------


def test_get_user_profile_excludes_private_fields():
    """Response must not expose email, oauth_id, oauth_provider, or nsfw_enabled."""
    user = _make_user(user_id=10, nsfw_enabled=True)

    app.dependency_overrides[get_db] = _override_db_returning(user)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.get("/api/users/10")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert "email" not in data
    assert "oauth_id" not in data
    assert "oauth_provider" not in data
    assert "nsfw_enabled" not in data


# ---------------------------------------------------------------------------
# No authentication required
# ---------------------------------------------------------------------------


def test_get_user_profile_requires_no_auth():
    """Endpoint is public — no auth cookie needed."""
    user = _make_user(user_id=1)

    app.dependency_overrides[get_db] = _override_db_returning(user)
    try:
        # No cookies set on client
        with TestClient(app, follow_redirects=False) as c:
            response = c.get("/api/users/1")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
