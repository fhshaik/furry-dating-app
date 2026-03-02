from types import SimpleNamespace
from unittest.mock import MagicMock


class TestInitSentry:
    def test_returns_false_when_dsn_is_missing(self):
        from app.core.config import Settings
        from app.core.sentry import init_sentry

        settings = Settings()

        assert init_sentry(settings) is False

    def test_initializes_sdk_when_dsn_is_configured(self, monkeypatch):
        from app.core.config import Settings
        from app.core.sentry import init_sentry

        sentry_sdk = SimpleNamespace(init=MagicMock())
        integration = object()
        fastapi_integration = SimpleNamespace(FastApiIntegration=MagicMock(return_value=integration))

        def fake_import(name: str):
            if name == "sentry_sdk":
                return sentry_sdk
            if name == "sentry_sdk.integrations.fastapi":
                return fastapi_integration
            raise ImportError(name)

        monkeypatch.setattr("app.core.sentry.import_module", fake_import)
        settings = Settings(
            sentry_dsn="https://examplePublicKey@o0.ingest.sentry.io/0",
            sentry_traces_sample_rate=0.5,
            environment="production",
        )

        assert init_sentry(settings) is True
        fastapi_integration.FastApiIntegration.assert_called_once_with()
        sentry_sdk.init.assert_called_once_with(
            dsn="https://examplePublicKey@o0.ingest.sentry.io/0",
            environment="production",
            traces_sample_rate=0.5,
            integrations=[integration],
        )

    def test_logs_warning_when_sdk_is_unavailable(self, monkeypatch, caplog):
        from app.core.config import Settings
        from app.core.sentry import init_sentry

        monkeypatch.setattr(
            "app.core.sentry.import_module",
            MagicMock(side_effect=ImportError("sentry_sdk")),
        )
        settings = Settings(sentry_dsn="https://examplePublicKey@o0.ingest.sentry.io/0")

        with caplog.at_level("WARNING"):
            assert init_sentry(settings) is False

        assert "sentry-sdk is not installed" in caplog.text
