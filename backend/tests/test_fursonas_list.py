"""Tests for GET /api/fursonas endpoint."""

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
    traits: list | None = None,
    description: str | None = None,
    image_url: str | None = None,
    is_primary: bool = False,
    is_nsfw: bool = False,
) -> MagicMock:
    fursona = MagicMock(spec=Fursona)
    fursona.id = fursona_id
    fursona.user_id = user_id
    fursona.name = name
    fursona.species = species
    fursona.traits = traits
    fursona.description = description
    fursona.image_url = image_url
    fursona.is_primary = is_primary
    fursona.is_nsfw = is_nsfw
    fursona.created_at = datetime(2025, 6, 1)
    return fursona


def _override_current_user(user: MagicMock):
    async def _override():
        return user

    return _override


def _override_db(fursonas: list):
    async def _db():
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = fursonas
        mock_session.execute.return_value = mock_result
        yield mock_session

    return _db


# ---------------------------------------------------------------------------
# Unauthenticated
# ---------------------------------------------------------------------------


def test_list_fursonas_unauthenticated_returns_401(client: TestClient):
    """No cookie → 401."""
    response = client.get("/api/fursonas")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Empty list
# ---------------------------------------------------------------------------


def test_list_fursonas_empty():
    """Authenticated user with no fursonas → empty list."""
    user = _make_user(user_id=1)

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db([])
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.get("/api/fursonas")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    assert response.json() == []


# ---------------------------------------------------------------------------
# Single fursona
# ---------------------------------------------------------------------------


def test_list_fursonas_single():
    """Authenticated user with one fursona → list with one item."""
    user = _make_user(user_id=2)
    fursona = _make_fursona(fursona_id=10, user_id=2, name="Shadow", species="Fox", is_primary=True)

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db([fursona])
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.get("/api/fursonas")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == 10
    assert data[0]["user_id"] == 2
    assert data[0]["name"] == "Shadow"
    assert data[0]["species"] == "Fox"
    assert data[0]["is_primary"] is True
    assert data[0]["is_nsfw"] is False


# ---------------------------------------------------------------------------
# Multiple fursonas
# ---------------------------------------------------------------------------


def test_list_fursonas_multiple():
    """Authenticated user with multiple fursonas → full list returned."""
    user = _make_user(user_id=3)
    fursonas = [
        _make_fursona(fursona_id=1, user_id=3, name="Blaze", species="Wolf", is_primary=True),
        _make_fursona(fursona_id=2, user_id=3, name="Frost", species="Dragon", is_nsfw=True),
        _make_fursona(fursona_id=3, user_id=3, name="Ember", species="Cat"),
    ]

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db(fursonas)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.get("/api/fursonas")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    names = {f["name"] for f in data}
    assert names == {"Blaze", "Frost", "Ember"}


# ---------------------------------------------------------------------------
# Response shape
# ---------------------------------------------------------------------------


def test_list_fursonas_response_fields():
    """Response includes all expected fields."""
    user = _make_user(user_id=4)
    fursona = _make_fursona(
        fursona_id=99,
        user_id=4,
        name="Luna",
        species="Rabbit",
        traits=["shy", "fluffy"],
        description="A shy rabbit",
        image_url="https://example.com/luna.png",
        is_primary=True,
        is_nsfw=False,
    )

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db([fursona])
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.get("/api/fursonas")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    item = response.json()[0]
    assert item["id"] == 99
    assert item["user_id"] == 4
    assert item["name"] == "Luna"
    assert item["species"] == "Rabbit"
    assert item["traits"] == ["shy", "fluffy"]
    assert item["description"] == "A shy rabbit"
    assert item["image_url"] == "https://example.com/luna.png"
    assert item["is_primary"] is True
    assert item["is_nsfw"] is False
    assert "created_at" in item
