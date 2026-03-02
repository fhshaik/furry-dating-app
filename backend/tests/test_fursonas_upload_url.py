"""Tests for GET /api/fursonas/:id/upload-url endpoint."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

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


def _make_fursona(fursona_id: int = 1, user_id: int = 1) -> MagicMock:
    fursona = MagicMock(spec=Fursona)
    fursona.id = fursona_id
    fursona.user_id = user_id
    fursona.name = "Blaze"
    fursona.species = "Wolf"
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


def _override_db(fursona: MagicMock | None):
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


def test_upload_url_unauthenticated_returns_401(client: TestClient):
    """No cookie → 401."""
    response = client.get("/api/fursonas/1/upload-url")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Not found
# ---------------------------------------------------------------------------


def test_upload_url_not_found_returns_404():
    """Fursona not found → 404."""
    user = _make_user()

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db(None)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.get("/api/fursonas/999/upload-url")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Forbidden (not owner)
# ---------------------------------------------------------------------------


def test_upload_url_wrong_owner_returns_403():
    """Fursona belongs to a different user → 403."""
    user = _make_user(user_id=1)
    fursona = _make_fursona(fursona_id=10, user_id=2)

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db(fursona)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.get("/api/fursonas/10/upload-url")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Successful response
# ---------------------------------------------------------------------------


def test_upload_url_returns_200_with_url_and_key():
    """Owner requests upload URL → 200 with upload_url and key."""
    user = _make_user(user_id=1)
    fursona = _make_fursona(fursona_id=5, user_id=1)

    fake_url = "https://s3.amazonaws.com/bucket/fursonas/5/abc?sig=x"
    fake_key = "fursonas/5/abc"
    fake_public_url = "https://bucket.s3.amazonaws.com/fursonas/5/abc"

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db(fursona)
    try:
        with patch(
            "app.routers.fursonas.generate_upload_url",
            return_value=(fake_url, fake_key, fake_public_url),
        ):
            with TestClient(app, follow_redirects=False) as c:
                response = c.get("/api/fursonas/5/upload-url")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert data["upload_url"] == fake_url
    assert data["key"] == fake_key
    assert data["public_url"] == fake_public_url


def test_upload_url_response_shape():
    """Response contains exactly upload_url and key fields."""
    user = _make_user(user_id=1)
    fursona = _make_fursona(fursona_id=3, user_id=1)

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db(fursona)
    try:
        with patch(
            "app.routers.fursonas.generate_upload_url",
            return_value=(
                "https://example.com/upload",
                "fursonas/3/uuid",
                "https://bucket.s3.amazonaws.com/fursonas/3/uuid",
            ),
        ):
            with TestClient(app, follow_redirects=False) as c:
                response = c.get("/api/fursonas/3/upload-url")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert "upload_url" in data
    assert "key" in data
    assert "public_url" in data


def test_upload_url_calls_generate_with_fursona_id():
    """generate_upload_url is called with the correct fursona_id."""
    user = _make_user(user_id=1)
    fursona = _make_fursona(fursona_id=7, user_id=1)

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db(fursona)
    try:
        with patch(
            "app.routers.fursonas.generate_upload_url",
            return_value=(
                "https://example.com/upload",
                "fursonas/7/uuid",
                "https://bucket.s3.amazonaws.com/fursonas/7/uuid",
            ),
        ) as mock_gen:
            with TestClient(app, follow_redirects=False) as c:
                c.get("/api/fursonas/7/upload-url?content_type=image/png")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    mock_gen.assert_called_once_with(7, "image/png")


def test_upload_url_s3_error_returns_500():
    """S3 failure (HTTPException from service) propagates as 500."""
    from fastapi import HTTPException as FastAPIHTTPException

    user = _make_user(user_id=1)
    fursona = _make_fursona(fursona_id=2, user_id=1)

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db(fursona)
    try:
        with patch(
            "app.routers.fursonas.generate_upload_url",
            side_effect=FastAPIHTTPException(status_code=500, detail="Failed to generate upload URL"),
        ):
            with TestClient(app, follow_redirects=False) as c:
                response = c.get("/api/fursonas/2/upload-url")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 500
    assert "upload URL" in response.json()["detail"]


def test_upload_url_rejects_non_image_content_type():
    """Non-image content types are rejected with 422."""
    user = _make_user(user_id=1)
    fursona = _make_fursona(fursona_id=4, user_id=1)

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db(fursona)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.get("/api/fursonas/4/upload-url?content_type=text/plain")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 422
    assert "content_type" in response.json()["detail"]


def test_upload_url_rejects_svg_content_type():
    """SVG (image/svg+xml) is rejected with 422 to prevent XSS via embedded script."""
    user = _make_user(user_id=1)
    fursona = _make_fursona(fursona_id=4, user_id=1)

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db(fursona)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.get("/api/fursonas/4/upload-url?content_type=image/svg%2Bxml")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 422
    assert "content_type" in response.json()["detail"]
