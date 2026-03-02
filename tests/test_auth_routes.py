"""Tests for the auth router: OAuth redirect flow and callback handling."""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_google_client(userinfo=None):
    if userinfo is None:
        userinfo = {"sub": "google-123", "email": "test@example.com", "name": "Test User"}

    mock_resp = MagicMock()
    mock_resp.json.return_value = userinfo
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.create_authorization_url = MagicMock(
        return_value=(
            "https://accounts.google.com/o/oauth2/auth?state=test-state",
            "test-state",
        )
    )
    mock_client.fetch_token = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    return mock_client


def _make_mock_discord_client(userinfo=None):
    if userinfo is None:
        userinfo = {"id": "discord-123", "email": "test@example.com", "username": "testuser"}

    mock_resp = MagicMock()
    mock_resp.json.return_value = userinfo
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.create_authorization_url = MagicMock(
        return_value=(
            "https://discord.com/oauth2/authorize?state=test-state",
            "test-state",
        )
    )
    mock_client.fetch_token = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    return mock_client


def _make_mock_db(existing_user=None):
    """Return a mock AsyncSession. Pass a User to simulate an existing record."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_user
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    async def _set_id(user):
        user.id = 1

    mock_session.refresh = AsyncMock(side_effect=_set_id)
    return mock_session


# ---------------------------------------------------------------------------
# Google login redirect
# ---------------------------------------------------------------------------


class TestGoogleLogin:
    def test_google_login_redirects(self):
        from app.main import app

        mock_client = _make_mock_google_client()
        with patch("app.routers.auth.create_google_client", return_value=mock_client):
            with TestClient(app, raise_server_exceptions=True) as client:
                response = client.get("/api/auth/google", follow_redirects=False)
        assert response.status_code in (302, 307)

    def test_google_login_redirects_to_google(self):
        from app.main import app

        mock_client = _make_mock_google_client()
        with patch("app.routers.auth.create_google_client", return_value=mock_client):
            with TestClient(app, raise_server_exceptions=True) as client:
                response = client.get("/api/auth/google", follow_redirects=False)
        assert "accounts.google.com" in response.headers["location"]


# ---------------------------------------------------------------------------
# Google callback — error cases
# ---------------------------------------------------------------------------


class TestGoogleCallbackErrors:
    def test_missing_code_returns_400(self):
        from app.main import app

        with TestClient(app, raise_server_exceptions=True) as client:
            response = client.get("/api/auth/google/callback", params={"state": "x"})
        assert response.status_code == 400

    def test_missing_code_returns_error_detail(self):
        from app.main import app

        with TestClient(app, raise_server_exceptions=True) as client:
            response = client.get("/api/auth/google/callback", params={"state": "x"})
        assert "code" in response.json()["detail"].lower()

    def test_state_mismatch_returns_400(self):
        from app.main import app

        with TestClient(app, raise_server_exceptions=True) as client:
            response = client.get(
                "/api/auth/google/callback",
                params={"code": "abc", "state": "wrong-state"},
            )
        assert response.status_code == 400

    def test_state_mismatch_returns_error_detail(self):
        from app.main import app

        with TestClient(app, raise_server_exceptions=True) as client:
            response = client.get(
                "/api/auth/google/callback",
                params={"code": "abc", "state": "wrong-state"},
            )
        assert "state" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Google callback — success
# ---------------------------------------------------------------------------


class TestGoogleCallbackSuccess:
    def _run_full_google_flow(self):
        from app.database import get_db
        from app.main import app

        mock_client = _make_mock_google_client()
        mock_db = _make_mock_db()

        async def override_get_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_get_db
        try:
            with patch("app.routers.auth.create_google_client", return_value=mock_client):
                with TestClient(app, raise_server_exceptions=True) as client:
                    # Initiate flow so session gets oauth_state
                    client.get("/api/auth/google", follow_redirects=False)
                    # Simulate provider redirecting back
                    response = client.get(
                        "/api/auth/google/callback",
                        params={"code": "auth-code", "state": "test-state"},
                        follow_redirects=False,
                    )
        finally:
            app.dependency_overrides.pop(get_db, None)
        return response

    def test_success_returns_redirect(self):
        response = self._run_full_google_flow()
        assert response.status_code in (302, 307)

    def test_success_redirects_to_auth_callback_page(self):
        response = self._run_full_google_flow()
        assert response.headers["location"].endswith("/auth/callback")

    def test_success_sets_access_token_cookie(self):
        response = self._run_full_google_flow()
        assert "access_token" in response.cookies

    def test_success_cookie_is_httponly(self):
        response = self._run_full_google_flow()
        set_cookie = response.headers.get("set-cookie", "")
        assert "httponly" in set_cookie.lower()


# ---------------------------------------------------------------------------
# Discord login redirect
# ---------------------------------------------------------------------------


class TestDiscordLogin:
    def test_discord_login_redirects(self):
        from app.main import app

        mock_client = _make_mock_discord_client()
        with patch("app.routers.auth.create_discord_client", return_value=mock_client):
            with TestClient(app, raise_server_exceptions=True) as client:
                response = client.get("/api/auth/discord", follow_redirects=False)
        assert response.status_code in (302, 307)

    def test_discord_login_redirects_to_discord(self):
        from app.main import app

        mock_client = _make_mock_discord_client()
        with patch("app.routers.auth.create_discord_client", return_value=mock_client):
            with TestClient(app, raise_server_exceptions=True) as client:
                response = client.get("/api/auth/discord", follow_redirects=False)
        assert "discord.com" in response.headers["location"]


# ---------------------------------------------------------------------------
# Discord callback — error cases
# ---------------------------------------------------------------------------


class TestDiscordCallbackErrors:
    def test_missing_code_returns_400(self):
        from app.main import app

        with TestClient(app, raise_server_exceptions=True) as client:
            response = client.get("/api/auth/discord/callback", params={"state": "x"})
        assert response.status_code == 400

    def test_state_mismatch_returns_400(self):
        from app.main import app

        with TestClient(app, raise_server_exceptions=True) as client:
            response = client.get(
                "/api/auth/discord/callback",
                params={"code": "abc", "state": "wrong-state"},
            )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Discord callback — success
# ---------------------------------------------------------------------------


class TestDiscordCallbackSuccess:
    def _run_full_discord_flow(self):
        from app.database import get_db
        from app.main import app

        mock_client = _make_mock_discord_client()
        mock_db = _make_mock_db()

        async def override_get_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_get_db
        try:
            with patch("app.routers.auth.create_discord_client", return_value=mock_client):
                with TestClient(app, raise_server_exceptions=True) as client:
                    client.get("/api/auth/discord", follow_redirects=False)
                    response = client.get(
                        "/api/auth/discord/callback",
                        params={"code": "auth-code", "state": "test-state"},
                        follow_redirects=False,
                    )
        finally:
            app.dependency_overrides.pop(get_db, None)
        return response

    def test_success_returns_redirect(self):
        response = self._run_full_discord_flow()
        assert response.status_code in (302, 307)

    def test_success_redirects_to_auth_callback_page(self):
        response = self._run_full_discord_flow()
        assert response.headers["location"].endswith("/auth/callback")

    def test_success_sets_access_token_cookie(self):
        response = self._run_full_discord_flow()
        assert "access_token" in response.cookies

    def test_success_cookie_is_httponly(self):
        response = self._run_full_discord_flow()
        set_cookie = response.headers.get("set-cookie", "")
        assert "httponly" in set_cookie.lower()
