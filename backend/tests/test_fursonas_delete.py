"""Tests for DELETE /api/fursonas/:id endpoint."""

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
) -> MagicMock:
    fursona = MagicMock(spec=Fursona)
    fursona.id = fursona_id
    fursona.user_id = user_id
    fursona.name = name
    fursona.species = species
    fursona.traits = None
    fursona.description = None
    fursona.image_url = None
    fursona.is_primary = False
    fursona.is_nsfw = False
    fursona.created_at = datetime(2025, 6, 1)
    return fursona


def _override_current_user(user: MagicMock):
    async def _override():
        return user

    return _override


def _override_db_delete(fursona: MagicMock | None):
    """DB override for delete: returns the fursona on execute, supports delete/commit."""

    async def _db():
        mock_session = AsyncMock()

        fetch_result = MagicMock()
        fetch_result.scalar_one_or_none.return_value = fursona

        mock_session.execute.return_value = fetch_result
        yield mock_session

    return _db


# ---------------------------------------------------------------------------
# Unauthenticated
# ---------------------------------------------------------------------------


def test_delete_fursona_unauthenticated_returns_401(client: TestClient):
    """No cookie → 401."""
    response = client.delete("/api/fursonas/1")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Not found
# ---------------------------------------------------------------------------


def test_delete_fursona_not_found_returns_404():
    """Fursona not found → 404."""
    user = _make_user()

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db_delete(None)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.delete("/api/fursonas/999")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Forbidden (not owner)
# ---------------------------------------------------------------------------


def test_delete_fursona_wrong_owner_returns_403():
    """Fursona belongs to a different user → 403."""
    user = _make_user(user_id=1)
    fursona = _make_fursona(fursona_id=10, user_id=2)  # owned by user 2

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db_delete(fursona)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.delete("/api/fursonas/10")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Successful deletion
# ---------------------------------------------------------------------------


def test_delete_fursona_returns_204():
    """Owner deletes fursona → 204 No Content."""
    user = _make_user(user_id=1)
    fursona = _make_fursona(fursona_id=10, user_id=1)

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db_delete(fursona)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.delete("/api/fursonas/10")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 204
    assert response.content == b""


def test_delete_fursona_calls_db_delete():
    """Delete calls db.delete and db.commit on the fursona object."""
    user = _make_user(user_id=1)
    fursona = _make_fursona(fursona_id=20, user_id=1)

    captured_session = None

    async def _db():
        nonlocal captured_session
        mock_session = AsyncMock()
        fetch_result = MagicMock()
        fetch_result.scalar_one_or_none.return_value = fursona
        mock_session.execute.return_value = fetch_result
        captured_session = mock_session
        yield mock_session

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _db
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.delete("/api/fursonas/20")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 204
    captured_session.delete.assert_called_once_with(fursona)
    captured_session.commit.assert_called_once()
