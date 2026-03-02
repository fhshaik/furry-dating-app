"""Tests for POST /api/fursonas endpoint."""

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


def _override_db_create(existing_count: int, created_fursona: MagicMock):
    """DB override for create: returns count on first execute, supports add/commit/refresh."""

    async def _db():
        mock_session = AsyncMock()

        count_result = MagicMock()
        count_result.scalar_one.return_value = existing_count
        mock_session.execute.return_value = count_result

        async def fake_refresh(obj):
            obj.id = created_fursona.id
            obj.user_id = created_fursona.user_id
            obj.name = created_fursona.name
            obj.species = created_fursona.species
            obj.traits = created_fursona.traits
            obj.description = created_fursona.description
            obj.image_url = created_fursona.image_url
            obj.is_primary = created_fursona.is_primary
            obj.is_nsfw = created_fursona.is_nsfw
            obj.created_at = created_fursona.created_at

        mock_session.refresh.side_effect = fake_refresh
        yield mock_session

    return _db


# ---------------------------------------------------------------------------
# Unauthenticated
# ---------------------------------------------------------------------------


def test_create_fursona_unauthenticated_returns_401(client: TestClient):
    """No cookie → 401."""
    response = client.post("/api/fursonas", json={"name": "Blaze", "species": "Wolf"})
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


def test_create_fursona_missing_name_returns_422():
    """Missing required 'name' → 422."""
    user = _make_user()

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db_create(0, MagicMock())
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.post("/api/fursonas", json={"species": "Wolf"})
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 422


def test_create_fursona_missing_species_returns_422():
    """Missing required 'species' → 422."""
    user = _make_user()

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db_create(0, MagicMock())
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.post("/api/fursonas", json={"name": "Blaze"})
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Max fursonas limit
# ---------------------------------------------------------------------------


def test_create_fursona_at_limit_returns_422():
    """User already has 5 fursonas → 422."""
    user = _make_user()

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db_create(5, MagicMock())
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.post("/api/fursonas", json={"name": "Nova", "species": "Fox"})
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 422
    assert "5" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Successful creation
# ---------------------------------------------------------------------------


def test_create_fursona_minimal_fields():
    """Create fursona with only required fields → 201 with defaults."""
    user = _make_user(user_id=1)
    created = _make_fursona(fursona_id=10, user_id=1, name="Blaze", species="Wolf")

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db_create(0, created)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.post("/api/fursonas", json={"name": "Blaze", "species": "Wolf"})
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == 10
    assert data["user_id"] == 1
    assert data["name"] == "Blaze"
    assert data["species"] == "Wolf"
    assert data["is_primary"] is False
    assert data["is_nsfw"] is False
    assert data["traits"] is None
    assert data["description"] is None
    assert data["image_url"] is None


def test_create_fursona_all_fields():
    """Create fursona with all optional fields → 201 with all fields returned."""
    user = _make_user(user_id=2)
    created = _make_fursona(
        fursona_id=20,
        user_id=2,
        name="Luna",
        species="Rabbit",
        traits=["shy", "fluffy"],
        description="A soft bunny",
        image_url="https://example.com/luna.png",
        is_primary=True,
        is_nsfw=False,
    )

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db_create(2, created)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.post(
                "/api/fursonas",
                json={
                    "name": "Luna",
                    "species": "Rabbit",
                    "traits": ["shy", "fluffy"],
                    "description": "A soft bunny",
                    "image_url": "https://example.com/luna.png",
                    "is_primary": True,
                    "is_nsfw": False,
                },
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == 20
    assert data["user_id"] == 2
    assert data["name"] == "Luna"
    assert data["species"] == "Rabbit"
    assert data["traits"] == ["shy", "fluffy"]
    assert data["description"] == "A soft bunny"
    assert data["image_url"] == "https://example.com/luna.png"
    assert data["is_primary"] is True
    assert data["is_nsfw"] is False
    assert "created_at" in data


def test_create_fursona_trims_strings_and_normalizes_blank_optionals():
    """Whitespace is trimmed and blank optional strings become null."""
    user = _make_user(user_id=21)
    created = _make_fursona(
        fursona_id=21,
        user_id=21,
        name="Luna",
        species="Rabbit",
        description=None,
        image_url=None,
    )

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db_create(0, created)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.post(
                "/api/fursonas",
                json={
                    "name": "  Luna  ",
                    "species": "  Rabbit  ",
                    "description": "   ",
                    "image_url": "   ",
                },
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Luna"
    assert data["species"] == "Rabbit"
    assert data["description"] is None
    assert data["image_url"] is None


def test_create_fursona_nsfw():
    """Create NSFW fursona → is_nsfw returned as True."""
    user = _make_user(user_id=3)
    created = _make_fursona(fursona_id=30, user_id=3, name="Shadow", species="Dragon", is_nsfw=True)

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db_create(1, created)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.post("/api/fursonas", json={"name": "Shadow", "species": "Dragon", "is_nsfw": True})
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 201
    assert response.json()["is_nsfw"] is True


def test_create_fursona_at_four_succeeds():
    """User with 4 fursonas can still create one more → 201."""
    user = _make_user(user_id=4)
    created = _make_fursona(fursona_id=40, user_id=4, name="Ember", species="Cat")

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db_create(4, created)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.post("/api/fursonas", json={"name": "Ember", "species": "Cat"})
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 201
    assert response.json()["name"] == "Ember"
