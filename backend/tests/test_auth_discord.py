"""Tests for Discord OAuth redirect and callback endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import Response as HttpxResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app


@pytest.fixture()
def client():
    """Synchronous test client (sufficient for redirect/response checks)."""
    with TestClient(app, follow_redirects=False) as c:
        yield c


# ---------------------------------------------------------------------------
# GET /api/auth/discord — redirect to Discord
# ---------------------------------------------------------------------------


def test_discord_login_redirects_to_discord(client: TestClient):
    """The login endpoint must redirect to Discord's authorize URL."""
    response = client.get("/api/auth/discord")
    assert response.status_code in (302, 307)
    location = response.headers["location"]
    assert "discord.com" in location
    assert "client_id" in location
    assert "redirect_uri" in location


def test_discord_login_redirect_contains_state(client: TestClient):
    """The redirect URL must include an OAuth state parameter."""
    response = client.get("/api/auth/discord")
    location = response.headers["location"]
    assert "state=" in location


def test_discord_login_redirect_uses_backend_url(client: TestClient):
    """The redirect_uri must come from configured backend_url, not proxy headers."""
    response = client.get("/api/auth/discord")
    location = response.headers["location"]
    assert "redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fapi%2Fauth%2Fdiscord%2Fcallback" in location


# ---------------------------------------------------------------------------
# GET /api/auth/discord/callback — exchange code, upsert user, set cookie
# ---------------------------------------------------------------------------


def _make_userinfo(discord_id="456789", email="discord@example.com", username="FurryUser") -> dict:
    return {"id": discord_id, "email": email, "username": username}


def _mock_httpx_response(json_data: dict, status_code: int = 200) -> HttpxResponse:
    resp = MagicMock(spec=HttpxResponse)
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    return resp


@patch("app.routers.auth.create_discord_client")
@patch("app.routers.auth.get_db")
def test_discord_callback_missing_code_returns_400(mock_get_db, mock_create_client, client: TestClient):
    """Callback without ?code= must return 400."""
    response = client.get("/api/auth/discord/callback")
    assert response.status_code == 400
    assert "code" in response.json()["detail"].lower()


@patch("app.routers.auth.create_discord_client")
@patch("app.routers.auth.get_db")
def test_discord_callback_state_mismatch_returns_400(
    mock_get_db, mock_create_client, client: TestClient
):
    """Callback with wrong state must return 400."""
    response = client.get("/api/auth/discord/callback?code=abc&state=wrongstate")
    assert response.status_code == 400
    assert "state" in response.json()["detail"].lower()


@patch("app.routers.auth.create_discord_client")
def test_discord_callback_creates_user_and_sets_cookie(mock_create_client: MagicMock):
    """
    Full happy-path: valid code + matching state → user created, cookie set,
    redirect to frontend.
    """
    from app.database import get_db
    from app.main import app as _app

    userinfo = _make_userinfo()

    # Build a mock OAuth client
    mock_oauth_client = MagicMock()
    mock_oauth_client.create_authorization_url.return_value = (
        "https://discord.com/oauth2/authorize?state=teststate&client_id=x",
        "teststate",
    )
    mock_oauth_client.fetch_token = AsyncMock(return_value={"access_token": "tok"})
    mock_oauth_client.get = AsyncMock(return_value=_mock_httpx_response(userinfo))
    mock_create_client.return_value = mock_oauth_client

    # Build a mock DB session that returns no existing user
    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    async def fake_refresh(obj):
        obj.id = 99

    mock_session.refresh = fake_refresh

    async def _db_override():
        yield mock_session

    _app.dependency_overrides[get_db] = _db_override
    try:
        with TestClient(_app, follow_redirects=False) as c:
            # Step 1: get a real state written into the session
            login_resp = c.get("/api/auth/discord")
            assert login_resp.status_code in (302, 307)

            # Step 2: call callback with matching state
            callback_resp = c.get(
                "/api/auth/discord/callback?code=authcode&state=teststate",
            )
    finally:
        _app.dependency_overrides.pop(get_db, None)

    assert callback_resp.status_code in (302, 307)
    assert "access_token" in callback_resp.cookies or "set-cookie" in {
        k.lower() for k in callback_resp.headers.keys()
    }


@patch("app.routers.auth.create_discord_client")
def test_discord_callback_cookie_is_httponly(mock_create_client: MagicMock):
    """The Set-Cookie header must have the HttpOnly flag."""
    from app.database import get_db
    from app.main import app as _app

    userinfo = _make_userinfo()

    mock_oauth_client = MagicMock()
    mock_oauth_client.create_authorization_url.return_value = (
        "https://discord.com/oauth2/authorize?state=httponly_state&client_id=x",
        "httponly_state",
    )
    mock_oauth_client.fetch_token = AsyncMock(return_value={"access_token": "tok"})
    mock_oauth_client.get = AsyncMock(return_value=_mock_httpx_response(userinfo))
    mock_create_client.return_value = mock_oauth_client

    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    async def fake_refresh(obj):
        obj.id = 20

    mock_session.refresh = fake_refresh

    async def _db_override():
        yield mock_session

    _app.dependency_overrides[get_db] = _db_override
    try:
        with TestClient(_app, follow_redirects=False) as c:
            c.get("/api/auth/discord")
            callback_resp = c.get(
                "/api/auth/discord/callback?code=authcode&state=httponly_state",
            )
    finally:
        _app.dependency_overrides.pop(get_db, None)

    assert callback_resp.status_code in (302, 307)
    set_cookie = callback_resp.headers.get("set-cookie", "")
    assert "access_token=" in set_cookie
    assert "httponly" in set_cookie.lower()


@patch("app.routers.auth.create_discord_client")
def test_discord_callback_cookie_contains_valid_jwt(mock_create_client: MagicMock):
    """The access_token cookie must contain a decodable JWT with correct sub claim."""
    from app.core.security import decode_access_token
    from app.database import get_db
    from app.main import app as _app

    userinfo = _make_userinfo()

    mock_oauth_client = MagicMock()
    mock_oauth_client.create_authorization_url.return_value = (
        "https://discord.com/oauth2/authorize?state=jwt_state&client_id=x",
        "jwt_state",
    )
    mock_oauth_client.fetch_token = AsyncMock(return_value={"access_token": "tok"})
    mock_oauth_client.get = AsyncMock(return_value=_mock_httpx_response(userinfo))
    mock_create_client.return_value = mock_oauth_client

    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    async def fake_refresh(obj):
        obj.id = 88

    mock_session.refresh = fake_refresh

    async def _db_override():
        yield mock_session

    _app.dependency_overrides[get_db] = _db_override
    try:
        with TestClient(_app, follow_redirects=False) as c:
            c.get("/api/auth/discord")
            callback_resp = c.get(
                "/api/auth/discord/callback?code=authcode&state=jwt_state",
            )
    finally:
        _app.dependency_overrides.pop(get_db, None)

    assert callback_resp.status_code in (302, 307)
    token = callback_resp.cookies.get("access_token")
    assert token is not None, "access_token cookie must be present"
    claims = decode_access_token(token)
    assert claims["sub"] == "88"


@patch("app.routers.auth.create_discord_client")
def test_discord_callback_updates_existing_user(mock_create_client: MagicMock):
    """
    When a user with the same discord oauth_id already exists,
    their email and display_name should be updated.
    """
    from app.database import get_db
    from app.main import app as _app

    userinfo = _make_userinfo(email="new@example.com", username="UpdatedUser")

    mock_oauth_client = MagicMock()
    mock_oauth_client.create_authorization_url.return_value = (
        "https://discord.com/oauth2/authorize?state=teststate2&client_id=x",
        "teststate2",
    )
    mock_oauth_client.fetch_token = AsyncMock(return_value={"access_token": "tok"})
    mock_oauth_client.get = AsyncMock(return_value=_mock_httpx_response(userinfo))
    mock_create_client.return_value = mock_oauth_client

    # Existing user with old data
    from app.models.user import User
    existing_user = MagicMock(spec=User)
    existing_user.id = 7
    existing_user.email = "old@example.com"
    existing_user.display_name = "OldUser"

    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_user
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()

    async def _db_override():
        yield mock_session

    _app.dependency_overrides[get_db] = _db_override
    try:
        with TestClient(_app, follow_redirects=False) as c:
            login_resp = c.get("/api/auth/discord")
            assert login_resp.status_code in (302, 307)

            callback_resp = c.get(
                "/api/auth/discord/callback?code=authcode&state=teststate2",
            )
    finally:
        _app.dependency_overrides.pop(get_db, None)

    assert callback_resp.status_code in (302, 307)
    # Verify the user fields were updated
    assert existing_user.email == "new@example.com"
    assert existing_user.display_name == "new@example.com"
    mock_session.commit.assert_awaited()
