"""Tests for Google OAuth redirect and callback endpoints."""

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
# GET /api/auth/google — redirect to Google
# ---------------------------------------------------------------------------


def test_google_login_redirects_to_google(client: TestClient):
    """The login endpoint must redirect to Google's authorize URL."""
    response = client.get("/api/auth/google")
    assert response.status_code in (302, 307)
    location = response.headers["location"]
    assert "accounts.google.com" in location
    assert "client_id" in location
    assert "redirect_uri" in location


def test_google_login_redirect_contains_state(client: TestClient):
    """The redirect URL must include an OAuth state parameter."""
    response = client.get("/api/auth/google")
    location = response.headers["location"]
    assert "state=" in location


def test_google_login_redirect_uses_backend_url(client: TestClient):
    """The redirect_uri must come from configured backend_url, not proxy headers."""
    response = client.get("/api/auth/google")
    location = response.headers["location"]
    assert "redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fapi%2Fauth%2Fgoogle%2Fcallback" in location


# ---------------------------------------------------------------------------
# GET /api/auth/google/callback — exchange code, upsert user, set cookie
# ---------------------------------------------------------------------------


def _make_userinfo(sub="123", email="test@example.com", name="Test User") -> dict:
    return {"sub": sub, "email": email, "name": name}


def _mock_httpx_response(json_data: dict, status_code: int = 200) -> HttpxResponse:
    resp = MagicMock(spec=HttpxResponse)
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    return resp


@pytest.fixture()
def client_with_state():
    """Client with a pre-seeded session state so callback validation passes."""
    with TestClient(app, follow_redirects=False) as c:
        # Seed a known state into the session cookie
        with c:
            # Trigger login to get a real session state written
            login_resp = c.get("/api/auth/google")
            assert login_resp.status_code in (302, 307)
        yield c


@patch("app.routers.auth.create_google_client")
@patch("app.routers.auth.get_db")
def test_callback_missing_code_returns_400(mock_get_db, mock_create_client, client: TestClient):
    """Callback without ?code= must return 400."""
    response = client.get("/api/auth/google/callback")
    assert response.status_code == 400
    assert "code" in response.json()["detail"].lower()


@patch("app.routers.auth.create_google_client")
@patch("app.routers.auth.get_db")
def test_callback_state_mismatch_returns_400(
    mock_get_db, mock_create_client, client: TestClient
):
    """Callback with wrong state must return 400."""
    response = client.get("/api/auth/google/callback?code=abc&state=wrongstate")
    assert response.status_code == 400
    assert "state" in response.json()["detail"].lower()


@patch("app.routers.auth.create_google_client")
def test_callback_creates_user_and_sets_cookie(mock_create_client: MagicMock):
    """
    Full happy-path: valid code + matching state → user created, cookie set,
    redirect to frontend.
    """
    from app.database import get_db
    from app.main import app as _app

    userinfo = _make_userinfo()

    # Build a mock OAuth client (create_authorization_url is sync, fetch_token/get are async)
    mock_oauth_client = MagicMock()
    mock_oauth_client.create_authorization_url.return_value = (
        "https://accounts.google.com/o/oauth2/v2/auth?state=teststate&client_id=x",
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
        obj.id = 42

    mock_session.refresh = fake_refresh

    async def _db_override():
        yield mock_session

    _app.dependency_overrides[get_db] = _db_override
    try:
        with TestClient(_app, follow_redirects=False) as c:
            # Step 1: get a real state written into the session
            login_resp = c.get("/api/auth/google")
            assert login_resp.status_code in (302, 307)

            # Step 2: call callback with matching state
            callback_resp = c.get(
                "/api/auth/google/callback?code=authcode&state=teststate",
            )
    finally:
        _app.dependency_overrides.pop(get_db, None)

    assert callback_resp.status_code in (302, 307)
    assert "access_token" in callback_resp.cookies or "set-cookie" in {
        k.lower() for k in callback_resp.headers.keys()
    }


@patch("app.routers.auth.create_google_client")
def test_google_callback_updates_existing_user(mock_create_client: MagicMock):
    """
    When a user with the same google oauth_id already exists,
    their email and display_name should be updated (upsert).
    """
    from app.database import get_db
    from app.main import app as _app

    userinfo = _make_userinfo(sub="123", email="new@example.com", name="New Name")

    mock_oauth_client = MagicMock()
    mock_oauth_client.create_authorization_url.return_value = (
        "https://accounts.google.com/o/oauth2/v2/auth?state=teststate3&client_id=x",
        "teststate3",
    )
    mock_oauth_client.fetch_token = AsyncMock(return_value={"access_token": "tok"})
    mock_oauth_client.get = AsyncMock(return_value=_mock_httpx_response(userinfo))
    mock_create_client.return_value = mock_oauth_client

    # Existing user with old data
    from app.models.user import User
    existing_user = MagicMock(spec=User)
    existing_user.id = 5
    existing_user.email = "old@example.com"
    existing_user.display_name = "Old Name"

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
            login_resp = c.get("/api/auth/google")
            assert login_resp.status_code in (302, 307)

            callback_resp = c.get(
                "/api/auth/google/callback?code=authcode&state=teststate3",
            )
    finally:
        _app.dependency_overrides.pop(get_db, None)

    assert callback_resp.status_code in (302, 307)
    # Verify the user fields were updated
    assert existing_user.email == "new@example.com"
    assert existing_user.display_name == "New Name"
    mock_session.commit.assert_awaited()


# ---------------------------------------------------------------------------
# Security helpers
# ---------------------------------------------------------------------------


@patch("app.routers.auth.create_google_client")
def test_google_callback_cookie_is_httponly(mock_create_client: MagicMock):
    """The Set-Cookie header must have the HttpOnly flag."""
    from app.database import get_db
    from app.main import app as _app

    userinfo = _make_userinfo()

    mock_oauth_client = MagicMock()
    mock_oauth_client.create_authorization_url.return_value = (
        "https://accounts.google.com/o/oauth2/v2/auth?state=httponly_state&client_id=x",
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
        obj.id = 10

    mock_session.refresh = fake_refresh

    async def _db_override():
        yield mock_session

    _app.dependency_overrides[get_db] = _db_override
    try:
        with TestClient(_app, follow_redirects=False) as c:
            c.get("/api/auth/google")
            callback_resp = c.get(
                "/api/auth/google/callback?code=authcode&state=httponly_state",
            )
    finally:
        _app.dependency_overrides.pop(get_db, None)

    assert callback_resp.status_code in (302, 307)
    set_cookie = callback_resp.headers.get("set-cookie", "")
    assert "access_token=" in set_cookie
    assert "httponly" in set_cookie.lower()


@patch("app.routers.auth.create_google_client")
def test_google_callback_cookie_contains_valid_jwt(mock_create_client: MagicMock):
    """The access_token cookie must contain a decodable JWT with correct sub claim."""
    from app.core.security import decode_access_token
    from app.database import get_db
    from app.main import app as _app

    userinfo = _make_userinfo()

    mock_oauth_client = MagicMock()
    mock_oauth_client.create_authorization_url.return_value = (
        "https://accounts.google.com/o/oauth2/v2/auth?state=jwt_state&client_id=x",
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
        obj.id = 77

    mock_session.refresh = fake_refresh

    async def _db_override():
        yield mock_session

    _app.dependency_overrides[get_db] = _db_override
    try:
        with TestClient(_app, follow_redirects=False) as c:
            c.get("/api/auth/google")
            callback_resp = c.get(
                "/api/auth/google/callback?code=authcode&state=jwt_state",
            )
    finally:
        _app.dependency_overrides.pop(get_db, None)

    assert callback_resp.status_code in (302, 307)
    token = callback_resp.cookies.get("access_token")
    assert token is not None, "access_token cookie must be present"
    claims = decode_access_token(token)
    assert claims["sub"] == "77"


def test_create_and_decode_access_token():
    """JWT round-trip: token created from user_id can be decoded back."""
    from app.core.security import create_access_token, decode_access_token

    token = create_access_token(user_id=99)
    assert isinstance(token, str)
    claims = decode_access_token(token)
    assert claims["sub"] == "99"


def test_decode_invalid_token_raises():
    """Decoding a garbage token must raise an error."""
    from authlib.jose.errors import JoseError

    from app.core.security import decode_access_token

    with pytest.raises((JoseError, Exception)):
        decode_access_token("not.a.valid.token")
