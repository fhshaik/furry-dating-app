"""Tests for the FastAPI application: CORS, lifespan, logging, and health endpoint."""

import json
import logging
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.rate_limit import RateLimiter

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client():
    """Return a synchronous TestClient for the FastAPI app."""
    # Import here so pytest can discover the module without a running server
    from app.main import app

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_ok(self, client):
        response = client.get("/health")
        assert response.json() == {"status": "ok"}

    def test_health_content_type_is_json(self, client):
        response = client.get("/health")
        assert "application/json" in response.headers["content-type"]


# ---------------------------------------------------------------------------
# API health endpoint
# ---------------------------------------------------------------------------


class TestApiHealthEndpoint:
    def test_api_health_returns_200(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200

    def test_api_health_returns_status_ok(self, client):
        response = client.get("/api/health")
        assert response.json()["status"] == "ok"

    def test_api_health_returns_version(self, client):
        response = client.get("/api/health")
        assert response.json()["version"] == "0.1.0"

    def test_api_health_content_type_is_json(self, client):
        response = client.get("/api/health")
        assert "application/json" in response.headers["content-type"]


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------


class TestRateLimiting:
    def test_api_health_returns_rate_limit_headers(self):
        from app.main import app

        original_limiter = app.state.rate_limiter
        app.state.rate_limiter = RateLimiter("2/minute")
        try:
            with TestClient(app, raise_server_exceptions=True) as c:
                response = c.get("/api/health", headers={"X-Forwarded-For": "198.51.100.10"})
        finally:
            app.state.rate_limiter = original_limiter

        assert response.status_code == 200
        assert response.headers["x-ratelimit-limit"] == "2"
        assert response.headers["x-ratelimit-remaining"] == "1"

    def test_api_health_returns_429_when_limit_is_exceeded(self):
        from app.main import app

        original_limiter = app.state.rate_limiter
        app.state.rate_limiter = RateLimiter("2/minute")
        try:
            with TestClient(app, raise_server_exceptions=True) as c:
                headers = {"X-Forwarded-For": "203.0.113.7"}
                assert c.get("/api/health", headers=headers).status_code == 200
                assert c.get("/api/health", headers=headers).status_code == 200
                response = c.get("/api/health", headers=headers)
        finally:
            app.state.rate_limiter = original_limiter

        assert response.status_code == 429
        assert response.json() == {"detail": "Rate limit exceeded"}
        assert response.headers["x-ratelimit-limit"] == "2"
        assert response.headers["x-ratelimit-remaining"] == "0"
        assert int(response.headers["retry-after"]) >= 1

    def test_rate_limit_is_scoped_per_client(self):
        from app.main import app

        original_limiter = app.state.rate_limiter
        app.state.rate_limiter = RateLimiter("1/minute")
        try:
            with TestClient(app, raise_server_exceptions=True) as c:
                first_client_headers = {"X-Forwarded-For": "203.0.113.11"}
                second_client_headers = {"X-Forwarded-For": "203.0.113.12"}
                assert c.get("/api/health", headers=first_client_headers).status_code == 200
                blocked_response = c.get("/api/health", headers=first_client_headers)
                allowed_response = c.get("/api/health", headers=second_client_headers)
        finally:
            app.state.rate_limiter = original_limiter

        assert blocked_response.status_code == 429
        assert allowed_response.status_code == 200


# ---------------------------------------------------------------------------
# API DB health endpoint
# ---------------------------------------------------------------------------


def _make_db_mock():
    """Return an async session mock that succeeds on execute."""
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=MagicMock())
    return mock_session


class TestApiHealthDbEndpoint:
    def test_db_health_returns_200(self):
        from app.database import get_db
        from app.main import app

        async def override_get_db():
            yield _make_db_mock()

        app.dependency_overrides[get_db] = override_get_db
        try:
            with TestClient(app, raise_server_exceptions=True) as c:
                response = c.get("/api/health/db")
            assert response.status_code == 200
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_db_health_returns_status_ok(self):
        from app.database import get_db
        from app.main import app

        async def override_get_db():
            yield _make_db_mock()

        app.dependency_overrides[get_db] = override_get_db
        try:
            with TestClient(app, raise_server_exceptions=True) as c:
                response = c.get("/api/health/db")
            assert response.json()["status"] == "ok"
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_db_health_returns_database_ok(self):
        from app.database import get_db
        from app.main import app

        async def override_get_db():
            yield _make_db_mock()

        app.dependency_overrides[get_db] = override_get_db
        try:
            with TestClient(app, raise_server_exceptions=True) as c:
                response = c.get("/api/health/db")
            assert response.json()["database"] == "ok"
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_db_health_content_type_is_json(self):
        from app.database import get_db
        from app.main import app

        async def override_get_db():
            yield _make_db_mock()

        app.dependency_overrides[get_db] = override_get_db
        try:
            with TestClient(app, raise_server_exceptions=True) as c:
                response = c.get("/api/health/db")
            assert "application/json" in response.headers["content-type"]
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_db_health_executes_select_1(self):
        from app.database import get_db
        from app.main import app

        mock_session = _make_db_mock()

        async def override_get_db():
            yield mock_session

        app.dependency_overrides[get_db] = override_get_db
        try:
            with TestClient(app, raise_server_exceptions=True) as c:
                c.get("/api/health/db")
            mock_session.execute.assert_called_once()
            call_arg = mock_session.execute.call_args[0][0]
            assert str(call_arg) == "SELECT 1"
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_db_health_returns_500_on_db_error(self):
        from app.database import get_db
        from app.main import app

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=Exception("connection refused"))

        async def override_get_db():
            yield mock_session

        app.dependency_overrides[get_db] = override_get_db
        try:
            with TestClient(app, raise_server_exceptions=False) as c:
                response = c.get("/api/health/db")
            assert response.status_code == 500
        finally:
            app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# App metadata
# ---------------------------------------------------------------------------


class TestAppMetadata:
    def test_app_title(self):
        from app.main import app

        assert app.title == "FurConnect API"

    def test_app_version(self):
        from app.main import app

        assert app.version == "0.1.0"

    def test_openapi_schema_is_accessible(self, client):
        response = client.get("/openapi.json")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# CORS middleware
# ---------------------------------------------------------------------------


class TestCORSMiddleware:
    def test_cors_header_for_allowed_origin(self, client):
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:5173"},
        )
        assert "access-control-allow-origin" in response.headers

    def test_cors_allows_configured_origin(self, client):
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:5173"},
        )
        assert response.headers["access-control-allow-origin"] == "http://localhost:5173"

    def test_cors_preflight_returns_200(self, client):
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code in (200, 204)

    def test_cors_allows_credentials(self, client):
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:5173"},
        )
        assert response.headers.get("access-control-allow-credentials") == "true"

    def test_cors_middleware_is_registered(self):
        from fastapi.middleware.cors import CORSMiddleware

        from app.main import app

        middleware_types = [m.cls for m in app.user_middleware]
        assert CORSMiddleware in middleware_types


# ---------------------------------------------------------------------------
# Settings / config
# ---------------------------------------------------------------------------


class TestSettings:
    def test_default_environment(self):
        from app.core.config import Settings

        s = Settings()
        assert s.environment == "development"

    def test_default_frontend_url(self):
        from app.core.config import Settings

        s = Settings()
        assert s.frontend_url == "http://localhost:5173"

    def test_cors_origins_includes_frontend_url(self):
        from app.core.config import Settings

        s = Settings()
        assert s.frontend_url in s.cors_origins

    def test_environment_override(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        from app.core.config import Settings

        s = Settings()
        assert s.environment == "production"

    def test_frontend_url_override(self, monkeypatch):
        monkeypatch.setenv("FRONTEND_URL", "https://example.com")
        from app.core.config import Settings

        s = Settings()
        assert "https://example.com" in s.cors_origins


# ---------------------------------------------------------------------------
# Structured logging
# ---------------------------------------------------------------------------


class TestStructuredLogging:
    def test_json_formatter_produces_valid_json(self):
        from app.core.logging import JSONFormatter

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="hello",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["message"] == "hello"

    def test_json_formatter_includes_required_fields(self):
        from app.core.logging import JSONFormatter

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="mylogger",
            level=logging.WARNING,
            pathname="",
            lineno=0,
            msg="test message",
            args=(),
            exc_info=None,
        )
        parsed = json.loads(formatter.format(record))
        assert "timestamp" in parsed
        assert "level" in parsed
        assert "logger" in parsed
        assert "message" in parsed

    def test_json_formatter_level_field(self):
        from app.core.logging import JSONFormatter

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="err",
            args=(),
            exc_info=None,
        )
        parsed = json.loads(formatter.format(record))
        assert parsed["level"] == "ERROR"

    def test_json_formatter_logger_name(self):
        from app.core.logging import JSONFormatter

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="app.main",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="x",
            args=(),
            exc_info=None,
        )
        parsed = json.loads(formatter.format(record))
        assert parsed["logger"] == "app.main"

    def test_json_formatter_includes_extra_fields(self):
        from app.core.logging import JSONFormatter

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="app.main",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="request complete",
            args=(),
            exc_info=None,
        )
        record.method = "GET"
        record.path = "/api/health"
        record.status_code = 200
        record.duration_ms = 12.34
        record.context = {"request_id": "req-123"}

        parsed = json.loads(formatter.format(record))
        assert parsed["method"] == "GET"
        assert parsed["path"] == "/api/health"
        assert parsed["status_code"] == 200
        assert parsed["duration_ms"] == 12.34
        assert parsed["context"] == {"request_id": "req-123"}

    def test_json_formatter_stringifies_non_json_extra_values(self):
        from app.core.logging import JSONFormatter

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="app.main",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="request complete",
            args=(),
            exc_info=None,
        )
        record.unsupported = object()

        parsed = json.loads(formatter.format(record))
        assert isinstance(parsed["unsupported"], str)

    def test_setup_logging_adds_stream_handler(self):
        from app.core.logging import setup_logging

        setup_logging()
        root = logging.getLogger()
        assert any(
            isinstance(h, logging.StreamHandler) for h in root.handlers
        )

    def test_setup_logging_uses_stdout(self):
        from app.core.logging import setup_logging

        setup_logging()
        root = logging.getLogger()
        stream_handlers = [
            h for h in root.handlers if isinstance(h, logging.StreamHandler)
        ]
        assert any(h.stream is sys.stdout for h in stream_handlers)

    def test_setup_logging_uses_json_formatter(self):
        from app.core.logging import JSONFormatter, setup_logging

        setup_logging()
        root = logging.getLogger()
        for handler in root.handlers:
            if isinstance(handler, logging.StreamHandler):
                assert isinstance(handler.formatter, JSONFormatter)
                return
        pytest.fail("No StreamHandler with JSONFormatter found")

    def test_request_logging_includes_structured_http_fields(self, monkeypatch):
        from app.main import app, logger

        entries = []

        def fake_info(message, *args, **kwargs):
            entries.append((message, kwargs.get("extra")))

        monkeypatch.setattr(logger, "info", fake_info)

        with TestClient(app, raise_server_exceptions=True) as c:
            response = c.get(
                "/api/health",
                headers={
                    "X-Forwarded-For": "198.51.100.20",
                    "X-Request-ID": "req-123",
                },
            )

        assert response.status_code == 200
        request_entries = [
            extra for message, extra in entries if message == "Request completed"
        ]
        assert len(request_entries) == 1
        entry = request_entries[0]
        assert entry["method"] == "GET"
        assert entry["path"] == "/api/health"
        assert entry["status_code"] == 200
        assert entry["client_ip"] == "198.51.100.20"
        assert entry["request_id"] == "req-123"
        assert entry["duration_ms"] >= 0
