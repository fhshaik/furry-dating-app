from unittest.mock import MagicMock

from fastapi.testclient import TestClient


class TestLifespan:
    def test_lifespan_initializes_sentry(self, monkeypatch):
        from app.main import app

        init_sentry_mock = MagicMock(return_value=True)
        monkeypatch.setattr("app.main.init_sentry", init_sentry_mock)

        with TestClient(app, raise_server_exceptions=True):
            pass

        init_sentry_mock.assert_called_once_with()
