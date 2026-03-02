"""Tests for the Match ORM model."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.match import Match
from app.models.user import User


@pytest.fixture()
async def sqlite_session():
    """Provide an in-memory SQLite async session with required tables created."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


def test_match_tablename():
    assert Match.__tablename__ == "matches"


def test_match_has_required_columns():
    column_names = set(Match.__table__.c.keys())
    assert "id" in column_names
    assert "user_a_id" in column_names
    assert "user_b_id" in column_names
    assert "created_at" in column_names
    assert "unmatched_at" in column_names


async def test_create_match_minimal(sqlite_session: AsyncSession):
    user_a = User(oauth_provider="google", oauth_id="match-a", display_name="Alpha")
    user_b = User(oauth_provider="google", oauth_id="match-b", display_name="Beta")
    sqlite_session.add_all([user_a, user_b])
    await sqlite_session.commit()

    match = Match(user_a_id=user_a.id, user_b_id=user_b.id)
    sqlite_session.add(match)
    await sqlite_session.commit()
    await sqlite_session.refresh(match)

    assert match.id is not None
    assert match.created_at is not None
    assert match.unmatched_at is None


async def test_unmatched_at_can_be_stored(sqlite_session: AsyncSession):
    from datetime import datetime, timezone

    user_a = User(oauth_provider="discord", oauth_id="match-c", display_name="Gamma")
    user_b = User(oauth_provider="discord", oauth_id="match-d", display_name="Delta")
    sqlite_session.add_all([user_a, user_b])
    await sqlite_session.commit()

    unmatched_at = datetime.now(timezone.utc).replace(tzinfo=None)
    match = Match(user_a_id=user_a.id, user_b_id=user_b.id, unmatched_at=unmatched_at)
    sqlite_session.add(match)
    await sqlite_session.commit()
    await sqlite_session.refresh(match)

    assert match.unmatched_at == unmatched_at
