"""Tests for DELETE /api/matches/:id endpoint."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
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


def test_delete_match_requires_auth(client: TestClient):
    response = client.delete("/api/matches/1")

    assert response.status_code == 401


async def test_delete_match_returns_404_for_missing_match(matches_session: AsyncSession):
    current_user = await _create_user(
        matches_session,
        "missing-match-current",
        "Current",
        created_at=datetime(2025, 1, 1),
    )

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(matches_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.delete("/api/matches/999")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 404
    assert response.json() == {"detail": "Match not found"}


async def test_delete_match_returns_404_for_already_unmatched_match(matches_session: AsyncSession):
    current_user = await _create_user(
        matches_session,
        "inactive-match-current",
        "Current",
        created_at=datetime(2025, 1, 1),
    )
    other_user = await _create_user(
        matches_session,
        "inactive-match-other",
        "Other",
        created_at=datetime(2025, 1, 2),
    )
    match = Match(
        user_a_id=current_user.id,
        user_b_id=other_user.id,
        created_at=datetime(2025, 2, 1, 8, 0, 0),
        unmatched_at=datetime(2025, 2, 2, 8, 0, 0),
    )
    matches_session.add(match)
    await matches_session.commit()
    await matches_session.refresh(match)

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(matches_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.delete(f"/api/matches/{match.id}")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 404
    assert response.json() == {"detail": "Match not found"}


async def test_delete_match_returns_403_for_non_participant(matches_session: AsyncSession):
    current_user = await _create_user(
        matches_session,
        "non-participant-current",
        "Current",
        created_at=datetime(2025, 1, 1),
    )
    user_a = await _create_user(
        matches_session,
        "non-participant-a",
        "User A",
        created_at=datetime(2025, 1, 2),
    )
    user_b = await _create_user(
        matches_session,
        "non-participant-b",
        "User B",
        created_at=datetime(2025, 1, 3),
    )
    match = Match(
        user_a_id=user_a.id,
        user_b_id=user_b.id,
        created_at=datetime(2025, 2, 1, 8, 0, 0),
    )
    matches_session.add(match)
    await matches_session.commit()
    await matches_session.refresh(match)

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(matches_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.delete(f"/api/matches/{match.id}")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 403
    assert response.json() == {"detail": "Not authorized to unmatch this user"}


async def test_delete_match_sets_unmatched_at_and_hides_match_from_list(matches_session: AsyncSession):
    current_user = await _create_user(
        matches_session,
        "delete-match-current",
        "Current",
        created_at=datetime(2025, 1, 1),
    )
    other_user = await _create_user(
        matches_session,
        "delete-match-other",
        "Other",
        created_at=datetime(2025, 1, 2),
    )
    match = Match(
        user_a_id=other_user.id,
        user_b_id=current_user.id,
        created_at=datetime(2025, 2, 1, 8, 0, 0),
    )
    matches_session.add(match)
    await matches_session.commit()
    await matches_session.refresh(match)

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(matches_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            delete_response = c.delete(f"/api/matches/{match.id}")
            list_response = c.get("/api/matches")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    refreshed_match = await matches_session.scalar(select(Match).where(Match.id == match.id))

    assert delete_response.status_code == 204
    assert delete_response.content == b""
    assert refreshed_match is not None
    assert refreshed_match.unmatched_at is not None
    assert list_response.status_code == 200
    assert list_response.json() == []
