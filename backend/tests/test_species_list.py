"""Tests for GET /api/species endpoint."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models.species_tag import SpeciesTag


@pytest.fixture()
def client():
    with TestClient(app, follow_redirects=False) as c:
        yield c


def _make_species_tag(tag_id: int, name: str, slug: str) -> MagicMock:
    tag = MagicMock(spec=SpeciesTag)
    tag.id = tag_id
    tag.name = name
    tag.slug = slug
    return tag


def _override_db(tags: list):
    async def _db():
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = tags
        mock_session.execute.return_value = mock_result
        yield mock_session

    return _db


# ---------------------------------------------------------------------------
# Empty list
# ---------------------------------------------------------------------------


def test_list_species_empty():
    """No species tags in DB → empty list."""
    app.dependency_overrides[get_db] = _override_db([])
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.get("/api/species")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    assert response.json() == []


# ---------------------------------------------------------------------------
# Single tag
# ---------------------------------------------------------------------------


def test_list_species_single():
    """One species tag → list with one item."""
    tag = _make_species_tag(1, "Wolf", "wolf")

    app.dependency_overrides[get_db] = _override_db([tag])
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.get("/api/species")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == 1
    assert data[0]["name"] == "Wolf"
    assert data[0]["slug"] == "wolf"


# ---------------------------------------------------------------------------
# Multiple tags
# ---------------------------------------------------------------------------


def test_list_species_multiple():
    """Multiple species tags → full list returned."""
    tags = [
        _make_species_tag(1, "Cat", "cat"),
        _make_species_tag(2, "Dragon", "dragon"),
        _make_species_tag(3, "Fox", "fox"),
    ]

    app.dependency_overrides[get_db] = _override_db(tags)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.get("/api/species")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    names = {t["name"] for t in data}
    assert names == {"Cat", "Dragon", "Fox"}


# ---------------------------------------------------------------------------
# Response shape
# ---------------------------------------------------------------------------


def test_list_species_response_fields():
    """Response includes id, name, and slug fields."""
    tag = _make_species_tag(42, "Snow Leopard", "snow-leopard")

    app.dependency_overrides[get_db] = _override_db([tag])
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.get("/api/species")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    item = response.json()[0]
    assert item["id"] == 42
    assert item["name"] == "Snow Leopard"
    assert item["slug"] == "snow-leopard"


# ---------------------------------------------------------------------------
# No auth required
# ---------------------------------------------------------------------------


def test_list_species_no_auth_required(client: TestClient):
    """Endpoint is public — no auth cookie needed (unauthenticated request succeeds with mocked DB)."""
    app.dependency_overrides[get_db] = _override_db([_make_species_tag(1, "Wolf", "wolf")])
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.get("/api/species")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
