"""Unit tests for require_nsfw_access FastAPI dependency."""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.core.deps import require_nsfw_access
from app.models.user import User


def _make_user(age: int | None = 25, nsfw_enabled: bool = True) -> MagicMock:
    user = MagicMock(spec=User)
    user.age = age
    user.nsfw_enabled = nsfw_enabled
    return user


# ---------------------------------------------------------------------------
# Age not confirmed
# ---------------------------------------------------------------------------


async def test_require_nsfw_access_no_age_raises_403():
    """User with age=None → 403 Age not confirmed."""
    user = _make_user(age=None)

    with pytest.raises(HTTPException) as exc_info:
        await require_nsfw_access(user=user)

    assert exc_info.value.status_code == 403
    assert "age not confirmed" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# Age below minimum
# ---------------------------------------------------------------------------


async def test_require_nsfw_access_underage_raises_403():
    """User under 18 → 403 with minimum age message."""
    user = _make_user(age=17, nsfw_enabled=True)

    with pytest.raises(HTTPException) as exc_info:
        await require_nsfw_access(user=user)

    assert exc_info.value.status_code == 403
    assert "18" in exc_info.value.detail


async def test_require_nsfw_access_age_zero_raises_403():
    """User with age=0 → 403."""
    user = _make_user(age=0, nsfw_enabled=True)

    with pytest.raises(HTTPException) as exc_info:
        await require_nsfw_access(user=user)

    assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# NSFW not enabled
# ---------------------------------------------------------------------------


async def test_require_nsfw_access_nsfw_disabled_raises_403():
    """User aged 18+ but nsfw_enabled=False → 403 NSFW content not enabled."""
    user = _make_user(age=25, nsfw_enabled=False)

    with pytest.raises(HTTPException) as exc_info:
        await require_nsfw_access(user=user)

    assert exc_info.value.status_code == 403
    assert "nsfw" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------


async def test_require_nsfw_access_exactly_18_passes():
    """User aged exactly 18 with nsfw_enabled → passes and returns user."""
    user = _make_user(age=18, nsfw_enabled=True)

    result = await require_nsfw_access(user=user)

    assert result is user


async def test_require_nsfw_access_adult_nsfw_enabled_passes():
    """User aged 25 with nsfw_enabled → passes and returns user."""
    user = _make_user(age=25, nsfw_enabled=True)

    result = await require_nsfw_access(user=user)

    assert result is user


async def test_require_nsfw_access_returns_user_object():
    """Ensure the returned object is the same user passed in."""
    user = _make_user(age=30, nsfw_enabled=True)

    result = await require_nsfw_access(user=user)

    assert result is user
