"""OAuth 2.0 client configuration using Authlib."""

from authlib.integrations.httpx_client import AsyncOAuth2Client

from app.core.config import settings

GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
GOOGLE_SCOPE = "openid email profile"

DISCORD_AUTHORIZE_URL = "https://discord.com/oauth2/authorize"
DISCORD_TOKEN_URL = "https://discord.com/api/oauth2/token"
DISCORD_USERINFO_URL = "https://discord.com/api/users/@me"
DISCORD_SCOPE = "identify email"


def create_google_client(redirect_uri: str) -> AsyncOAuth2Client:
    """Return an Authlib AsyncOAuth2Client configured for Google."""
    return AsyncOAuth2Client(
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scope=GOOGLE_SCOPE,
        redirect_uri=redirect_uri,
    )


def create_discord_client(redirect_uri: str) -> AsyncOAuth2Client:
    """Return an Authlib AsyncOAuth2Client configured for Discord."""
    return AsyncOAuth2Client(
        client_id=settings.discord_client_id,
        client_secret=settings.discord_client_secret,
        scope=DISCORD_SCOPE,
        redirect_uri=redirect_uri,
    )
