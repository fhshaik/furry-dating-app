"""Tests for PATCH /api/fursonas/:id endpoint."""

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


def _override_db_update(fursona: MagicMock | None):
    """DB override for update: returns the fursona on execute, supports commit/refresh."""

    async def _db():
        mock_session = AsyncMock()

        fetch_result = MagicMock()
        fetch_result.scalar_one_or_none.return_value = fursona

        async def fake_refresh(obj):
            pass

        mock_session.execute.return_value = fetch_result
        mock_session.refresh.side_effect = fake_refresh
        yield mock_session

    return _db


# ---------------------------------------------------------------------------
# Unauthenticated
# ---------------------------------------------------------------------------


def test_update_fursona_unauthenticated_returns_401(client: TestClient):
    """No cookie → 401."""
    response = client.patch("/api/fursonas/1", json={"name": "NewName"})
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Not found
# ---------------------------------------------------------------------------


def test_update_fursona_not_found_returns_404():
    """Fursona not found → 404."""
    user = _make_user()

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db_update(None)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.patch("/api/fursonas/999", json={"name": "Ghost"})
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Forbidden (not owner)
# ---------------------------------------------------------------------------


def test_update_fursona_wrong_owner_returns_403():
    """Fursona belongs to a different user → 403."""
    user = _make_user(user_id=1)
    fursona = _make_fursona(fursona_id=10, user_id=2)  # owned by user 2

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db_update(fursona)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.patch("/api/fursonas/10", json={"name": "Hacked"})
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Successful updates
# ---------------------------------------------------------------------------


def test_update_fursona_name():
    """Patch name only → updated name returned."""
    user = _make_user(user_id=1)
    fursona = _make_fursona(fursona_id=10, user_id=1, name="Blaze", species="Wolf")

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db_update(fursona)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.patch("/api/fursonas/10", json={"name": "Inferno"})
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    # setattr was called on the mock, so name was mutated
    assert fursona.name == "Inferno"


def test_update_fursona_species():
    """Patch species only → updated species."""
    user = _make_user(user_id=1)
    fursona = _make_fursona(fursona_id=11, user_id=1, name="Frost", species="Dragon")

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db_update(fursona)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.patch("/api/fursonas/11", json={"species": "Ice Dragon"})
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    assert fursona.species == "Ice Dragon"


def test_update_fursona_multiple_fields():
    """Patch multiple fields at once."""
    user = _make_user(user_id=2)
    fursona = _make_fursona(fursona_id=20, user_id=2, name="Luna", species="Rabbit")

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db_update(fursona)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.patch(
                "/api/fursonas/20",
                json={
                    "name": "Moonbeam",
                    "description": "A glowing rabbit",
                    "is_primary": True,
                    "traits": ["gentle", "glowing"],
                },
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    assert fursona.name == "Moonbeam"
    assert fursona.description == "A glowing rabbit"
    assert fursona.is_primary is True
    assert fursona.traits == ["gentle", "glowing"]


def test_update_fursona_trims_strings_and_normalizes_blank_optionals():
    """Whitespace is trimmed and blank optional strings become null."""
    user = _make_user(user_id=6)
    fursona = _make_fursona(
        fursona_id=60,
        user_id=6,
        name="Nova",
        species="Fox",
        description="Old desc",
        image_url="https://example.com/nova.png",
    )

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db_update(fursona)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.patch(
                "/api/fursonas/60",
                json={
                    "name": "  Ember  ",
                    "species": "  Wolf  ",
                    "description": "   ",
                    "image_url": "   ",
                },
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    assert fursona.name == "Ember"
    assert fursona.species == "Wolf"
    assert fursona.description is None
    assert fursona.image_url is None


def test_update_fursona_empty_body_is_noop():
    """Empty patch body → 200, nothing changes."""
    user = _make_user(user_id=3)
    fursona = _make_fursona(fursona_id=30, user_id=3, name="Shadow", species="Cat")

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db_update(fursona)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.patch("/api/fursonas/30", json={})
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200


def test_update_fursona_set_nsfw():
    """Patch is_nsfw → flag updated."""
    user = _make_user(user_id=4)
    fursona = _make_fursona(fursona_id=40, user_id=4, name="Ember", species="Fox", is_nsfw=False)

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db_update(fursona)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.patch("/api/fursonas/40", json={"is_nsfw": True})
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    assert fursona.is_nsfw is True


def test_update_fursona_response_shape():
    """Response includes all expected fields."""
    user = _make_user(user_id=5)
    fursona = _make_fursona(
        fursona_id=50,
        user_id=5,
        name="Nova",
        species="Deer",
        traits=["bright"],
        description="A bright deer",
        image_url="https://example.com/nova.png",
        is_primary=True,
        is_nsfw=False,
    )

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db_update(fursona)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.patch("/api/fursonas/50", json={"description": "Updated desc"})
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "user_id" in data
    assert "name" in data
    assert "species" in data
    assert "traits" in data
    assert "description" in data
    assert "image_url" in data
    assert "is_primary" in data
    assert "is_nsfw" in data
    assert "created_at" in data
