"""Tests for POST /api/auth/logout endpoint."""

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.main import app


@pytest.fixture()
def client():
    with TestClient(app, follow_redirects=False) as c:
        yield c


def test_logout_returns_200(client: TestClient):
    """POST /api/auth/logout must return 200."""
    response = client.post("/api/auth/logout")
    assert response.status_code == 200


def test_logout_returns_message(client: TestClient):
    """Response body must contain a message field."""
    response = client.post("/api/auth/logout")
    assert response.json() == {"message": "Logged out"}


def test_logout_clears_cookie(client: TestClient):
    """Response Set-Cookie header must expire the access_token cookie (max-age=0)."""
    token = create_access_token(user_id=1)
    client.cookies.set("access_token", token)

    response = client.post("/api/auth/logout")

    set_cookie = response.headers.get("set-cookie", "")
    assert "access_token" in set_cookie
    assert "max-age=0" in set_cookie.lower()


def test_logout_set_cookie_header_present(client: TestClient):
    """Response must include a Set-Cookie header that clears access_token."""
    response = client.post("/api/auth/logout")
    set_cookie = response.headers.get("set-cookie", "")
    assert "access_token" in set_cookie


def test_logout_without_cookie_still_returns_200(client: TestClient):
    """Logout must succeed even when no cookie is present (idempotent)."""
    response = client.post("/api/auth/logout")
    assert response.status_code == 200
    assert response.json() == {"message": "Logged out"}
