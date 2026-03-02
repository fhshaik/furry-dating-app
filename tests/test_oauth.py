"""Tests for OAuth 2.0 client configuration (authlib)."""

from authlib.integrations.httpx_client import AsyncOAuth2Client


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestOAuthConstants:
    def test_google_authorize_url(self):
        from app.core.oauth import GOOGLE_AUTHORIZE_URL

        assert GOOGLE_AUTHORIZE_URL == "https://accounts.google.com/o/oauth2/v2/auth"

    def test_google_token_url(self):
        from app.core.oauth import GOOGLE_TOKEN_URL

        assert GOOGLE_TOKEN_URL == "https://oauth2.googleapis.com/token"

    def test_google_userinfo_url(self):
        from app.core.oauth import GOOGLE_USERINFO_URL

        assert GOOGLE_USERINFO_URL == "https://openidconnect.googleapis.com/v1/userinfo"

    def test_google_scope(self):
        from app.core.oauth import GOOGLE_SCOPE

        assert "openid" in GOOGLE_SCOPE
        assert "email" in GOOGLE_SCOPE
        assert "profile" in GOOGLE_SCOPE

    def test_discord_authorize_url(self):
        from app.core.oauth import DISCORD_AUTHORIZE_URL

        assert DISCORD_AUTHORIZE_URL == "https://discord.com/oauth2/authorize"

    def test_discord_token_url(self):
        from app.core.oauth import DISCORD_TOKEN_URL

        assert DISCORD_TOKEN_URL == "https://discord.com/api/oauth2/token"

    def test_discord_userinfo_url(self):
        from app.core.oauth import DISCORD_USERINFO_URL

        assert DISCORD_USERINFO_URL == "https://discord.com/api/users/@me"

    def test_discord_scope(self):
        from app.core.oauth import DISCORD_SCOPE

        assert "identify" in DISCORD_SCOPE
        assert "email" in DISCORD_SCOPE


# ---------------------------------------------------------------------------
# Google client factory
# ---------------------------------------------------------------------------


class TestCreateGoogleClient:
    def test_returns_async_oauth2_client(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "g-id")
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "g-secret")
        from app.core import oauth
        from app.core.config import Settings

        oauth.settings = Settings()
        client = oauth.create_google_client("https://example.com/callback")
        assert isinstance(client, AsyncOAuth2Client)

    def test_client_id_is_set(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "my-google-id")
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "my-google-secret")
        from app.core import oauth
        from app.core.config import Settings

        oauth.settings = Settings()
        client = oauth.create_google_client("https://example.com/callback")
        assert client.client_id == "my-google-id"

    def test_redirect_uri_is_set(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "g-id")
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "g-secret")
        from app.core import oauth
        from app.core.config import Settings

        oauth.settings = Settings()
        redirect = "https://example.com/auth/google/callback"
        client = oauth.create_google_client(redirect)
        assert client.redirect_uri == redirect

    def test_scope_contains_openid(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "g-id")
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "g-secret")
        from app.core import oauth
        from app.core.config import Settings

        oauth.settings = Settings()
        client = oauth.create_google_client("https://example.com/callback")
        assert "openid" in (client.scope or "")

    def test_scope_contains_email(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "g-id")
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "g-secret")
        from app.core import oauth
        from app.core.config import Settings

        oauth.settings = Settings()
        client = oauth.create_google_client("https://example.com/callback")
        assert "email" in (client.scope or "")

    def test_scope_contains_profile(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "g-id")
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "g-secret")
        from app.core import oauth
        from app.core.config import Settings

        oauth.settings = Settings()
        client = oauth.create_google_client("https://example.com/callback")
        assert "profile" in (client.scope or "")


# ---------------------------------------------------------------------------
# Discord client factory
# ---------------------------------------------------------------------------


class TestCreateDiscordClient:
    def test_returns_async_oauth2_client(self, monkeypatch):
        monkeypatch.setenv("DISCORD_CLIENT_ID", "d-id")
        monkeypatch.setenv("DISCORD_CLIENT_SECRET", "d-secret")
        from app.core import oauth
        from app.core.config import Settings

        oauth.settings = Settings()
        client = oauth.create_discord_client("https://example.com/callback")
        assert isinstance(client, AsyncOAuth2Client)

    def test_client_id_is_set(self, monkeypatch):
        monkeypatch.setenv("DISCORD_CLIENT_ID", "my-discord-id")
        monkeypatch.setenv("DISCORD_CLIENT_SECRET", "my-discord-secret")
        from app.core import oauth
        from app.core.config import Settings

        oauth.settings = Settings()
        client = oauth.create_discord_client("https://example.com/callback")
        assert client.client_id == "my-discord-id"

    def test_redirect_uri_is_set(self, monkeypatch):
        monkeypatch.setenv("DISCORD_CLIENT_ID", "d-id")
        monkeypatch.setenv("DISCORD_CLIENT_SECRET", "d-secret")
        from app.core import oauth
        from app.core.config import Settings

        oauth.settings = Settings()
        redirect = "https://example.com/auth/discord/callback"
        client = oauth.create_discord_client(redirect)
        assert client.redirect_uri == redirect

    def test_scope_contains_identify(self, monkeypatch):
        monkeypatch.setenv("DISCORD_CLIENT_ID", "d-id")
        monkeypatch.setenv("DISCORD_CLIENT_SECRET", "d-secret")
        from app.core import oauth
        from app.core.config import Settings

        oauth.settings = Settings()
        client = oauth.create_discord_client("https://example.com/callback")
        assert "identify" in (client.scope or "")

    def test_scope_contains_email(self, monkeypatch):
        monkeypatch.setenv("DISCORD_CLIENT_ID", "d-id")
        monkeypatch.setenv("DISCORD_CLIENT_SECRET", "d-secret")
        from app.core import oauth
        from app.core.config import Settings

        oauth.settings = Settings()
        client = oauth.create_discord_client("https://example.com/callback")
        assert "email" in (client.scope or "")


# ---------------------------------------------------------------------------
# Module-level importability
# ---------------------------------------------------------------------------


class TestOAuthModuleImport:
    def test_module_is_importable(self):
        import app.core.oauth  # noqa: F401

    def test_create_google_client_is_callable(self):
        from app.core.oauth import create_google_client

        assert callable(create_google_client)

    def test_create_discord_client_is_callable(self):
        from app.core.oauth import create_discord_client

        assert callable(create_discord_client)
