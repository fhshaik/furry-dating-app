import logging
from importlib import import_module

from app.core.config import Settings, settings

logger = logging.getLogger(__name__)


def init_sentry(settings_obj: Settings = settings) -> bool:
    """Initialize Sentry when a DSN is configured."""
    if not settings_obj.sentry_enabled:
        return False

    try:
        sentry_sdk = import_module("sentry_sdk")
        fastapi_integration = import_module("sentry_sdk.integrations.fastapi")
    except ImportError:
        logger.warning("Sentry DSN configured but sentry-sdk is not installed")
        return False

    sentry_sdk.init(
        dsn=settings_obj.sentry_dsn.strip(),
        environment=settings_obj.environment,
        traces_sample_rate=settings_obj.sentry_traces_sample_rate,
        integrations=[fastapi_integration.FastApiIntegration()],
    )
    return True
