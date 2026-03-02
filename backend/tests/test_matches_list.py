"""Tests for GET /api/matches endpoint."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.deps import get_current_user
from app.database import Base, get_db
from app.main import app
from app.models.match import Match
from app.models.user import User


@pytest.fixture()
async def matches_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture()
def client():
    with TestClient(app, follow_redirects=False) as c:
        yield c


def _override_current_user(user: User):
    async def _override():
        return user

    return _override


def _override_db(session: AsyncSession):
    async def _db():
        yield session

    return _db


async def _create_user(
    session: AsyncSession,
    oauth_id: str,
    display_name: str,
    *,
    created_at: datetime,
) -> User:
    user = User(
        oauth_provider="google",
        oauth_id=oauth_id,
        email=f"{oauth_id}@example.com",
        display_name=display_name,
        bio=f"{display_name} bio",
        age=24,
        city="Seattle",
        relationship_style="monogamous",
        created_at=created_at,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


def test_list_matches_requires_auth(client: TestClient):
    response = client.get("/api/matches")

    assert response.status_code == 401


async def test_list_matches_returns_active_matches_for_both_directions(
    matches_session: AsyncSession,
):
    current_user = await _create_user(
        matches_session,
        "matches-current",
        "Current",
        created_at=datetime(2025, 1, 1),
    )
    older_match_user = await _create_user(
        matches_session,
        "matches-older",
        "Older",
        created_at=datetime(2025, 1, 2),
    )
    newer_match_user = await _create_user(
        matches_session,
        "matches-newer",
        "Newer",
        created_at=datetime(2025, 1, 3),
    )
    inactive_match_user = await _create_user(
        matches_session,
        "matches-inactive",
        "Inactive",
        created_at=datetime(2025, 1, 4),
    )
    unrelated_user = await _create_user(
        matches_session,
        "matches-unrelated",
        "Unrelated",
        created_at=datetime(2025, 1, 5),
    )

    matches_session.add_all(
        [
            Match(
                user_a_id=current_user.id,
                user_b_id=older_match_user.id,
                created_at=datetime(2025, 2, 1, 8, 0, 0),
            ),
            Match(
                user_a_id=newer_match_user.id,
                user_b_id=current_user.id,
                created_at=datetime(2025, 2, 2, 8, 0, 0),
            ),
            Match(
                user_a_id=current_user.id,
                user_b_id=inactive_match_user.id,
                created_at=datetime(2025, 2, 3, 8, 0, 0),
                unmatched_at=datetime(2025, 2, 4, 8, 0, 0),
            ),
            Match(
                user_a_id=older_match_user.id,
                user_b_id=unrelated_user.id,
                created_at=datetime(2025, 2, 5, 8, 0, 0),
            ),
        ]
    )
    await matches_session.commit()

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(matches_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.get("/api/matches")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert [item["matched_user"]["id"] for item in data] == [
        newer_match_user.id,
        older_match_user.id,
    ]
    assert [item["matched_user"]["display_name"] for item in data] == ["Newer", "Older"]
    assert all("email" not in item["matched_user"] for item in data)
    assert all("oauth_provider" not in item["matched_user"] for item in data)
    assert all(item["matched_user"]["id"] != inactive_match_user.id for item in data)
    assert [item["last_message_preview"] for item in data] == [None, None]
