"""Tests for POST /api/fursonas/:id/primary endpoint."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.deps import get_current_user
from app.database import get_db
from app.main import app
from app.models.fursona import Fursona
from app.models.user import User


@pytest.fixture()
def client():
    with TestClient(app, follow_redirects=False) as c:
        yield c


def _make_user(user_id: int = 1) -> MagicMock:
    user = MagicMock(spec=User)
    user.id = user_id
    user.display_name = "Test User"
    user.created_at = datetime(2025, 1, 1)
    return user


def _make_fursona(
    fursona_id: int = 1,
    user_id: int = 1,
    name: str = "Blaze",
    species: str = "Wolf",
    is_primary: bool = False,
) -> MagicMock:
    fursona = MagicMock(spec=Fursona)
    fursona.id = fursona_id
    fursona.user_id = user_id
    fursona.name = name
    fursona.species = species
    fursona.traits = None
    fursona.description = None
    fursona.image_url = None
    fursona.is_primary = is_primary
    fursona.is_nsfw = False
    fursona.created_at = datetime(2025, 6, 1)
    return fursona


def _override_current_user(user: MagicMock):
    async def _override():
        return user

    return _override


def _override_db_set_primary(fursona: MagicMock | None):
    """DB override: first execute returns the fursona fetch, second execute is the bulk update."""

    async def _db():
        mock_session = AsyncMock()

        fetch_result = MagicMock()
        fetch_result.scalar_one_or_none.return_value = fursona

        # First call: SELECT fursona by id; second call: UPDATE all fursonas
        mock_session.execute.side_effect = [fetch_result, MagicMock()]
        yield mock_session

    return _db


# ---------------------------------------------------------------------------
# Unauthenticated
# ---------------------------------------------------------------------------


def test_set_primary_unauthenticated_returns_401(client: TestClient):
    """No cookie → 401."""
    response = client.post("/api/fursonas/1/primary")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Not found
# ---------------------------------------------------------------------------


def test_set_primary_not_found_returns_404():
    """Fursona not found → 404."""
    user = _make_user()

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db_set_primary(None)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.post("/api/fursonas/999/primary")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Forbidden (not owner)
# ---------------------------------------------------------------------------


def test_set_primary_wrong_owner_returns_403():
    """Fursona belongs to a different user → 403."""
    user = _make_user(user_id=1)
    fursona = _make_fursona(fursona_id=10, user_id=2)  # owned by user 2

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db_set_primary(fursona)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.post("/api/fursonas/10/primary")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Successful set primary
# ---------------------------------------------------------------------------


def test_set_primary_returns_200_with_fursona():
    """Owner sets fursona as primary → 200 with updated fursona."""
    user = _make_user(user_id=1)
    fursona = _make_fursona(fursona_id=5, user_id=1, is_primary=False)

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db_set_primary(fursona)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.post("/api/fursonas/5/primary")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 5
    assert data["is_primary"] is True


def test_set_primary_already_primary_returns_200():
    """Fursona already marked primary → still returns 200."""
    user = _make_user(user_id=1)
    fursona = _make_fursona(fursona_id=3, user_id=1, is_primary=True)

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db_set_primary(fursona)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.post("/api/fursonas/3/primary")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    assert response.json()["is_primary"] is True


def test_set_primary_calls_bulk_update_and_sets_flag():
    """Endpoint clears all primaries via bulk UPDATE and sets is_primary=True on target."""
    user = _make_user(user_id=1)
    fursona = _make_fursona(fursona_id=7, user_id=1, is_primary=False)

    captured_session = None

    async def _db():
        nonlocal captured_session
        mock_session = AsyncMock()

        fetch_result = MagicMock()
        fetch_result.scalar_one_or_none.return_value = fursona
        mock_session.execute.side_effect = [fetch_result, MagicMock()]

        captured_session = mock_session
        yield mock_session

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _db
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.post("/api/fursonas/7/primary")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    # Two execute calls: SELECT + UPDATE
    assert captured_session.execute.call_count == 2
    assert fursona.is_primary is True
    captured_session.commit.assert_called_once()


def test_set_primary_response_shape():
    """Response includes all expected fursona fields."""
    user = _make_user(user_id=1)
    fursona = _make_fursona(fursona_id=2, user_id=1)

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db_set_primary(fursona)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.post("/api/fursonas/2/primary")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    for field in ("id", "user_id", "name", "species", "traits", "description",
                  "image_url", "is_primary", "is_nsfw", "created_at"):
        assert field in data, f"Missing field: {field}"
