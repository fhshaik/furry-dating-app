"""Tests for the Pack ORM model."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.pack import Pack
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


def test_pack_tablename():
    assert Pack.__tablename__ == "packs"


def test_pack_has_required_columns():
    column_names = set(Pack.__table__.c.keys())
    assert "id" in column_names
    assert "creator_id" in column_names
    assert "name" in column_names
    assert "description" in column_names
    assert "image_url" in column_names
    assert "species_tags" in column_names
    assert "max_size" in column_names
    assert "consensus_required" in column_names
    assert "is_open" in column_names
    assert "created_at" in column_names


async def test_create_pack_minimal(sqlite_session: AsyncSession):
    creator = User(oauth_provider="google", oauth_id="pack-a", display_name="Creator")
    sqlite_session.add(creator)
    await sqlite_session.commit()

    pack = Pack(creator_id=creator.id, name="North Pack")
    sqlite_session.add(pack)
    await sqlite_session.commit()
    await sqlite_session.refresh(pack)

    assert pack.id is not None
    assert pack.max_size == 10
    assert pack.consensus_required is False
    assert pack.is_open is True
    assert pack.created_at is not None


async def test_create_pack_with_optional_fields(sqlite_session: AsyncSession):
    creator = User(oauth_provider="discord", oauth_id="pack-b", display_name="Founder")
    sqlite_session.add(creator)
    await sqlite_session.commit()

    pack = Pack(
        creator_id=creator.id,
        name="Aurora Pack",
        description="A small, social group.",
        image_url="https://example.com/aurora-pack.png",
        species_tags=["wolf", "fox"],
        max_size=6,
        consensus_required=True,
        is_open=False,
    )
    sqlite_session.add(pack)
    await sqlite_session.commit()
    await sqlite_session.refresh(pack)

    assert pack.description == "A small, social group."
    assert pack.image_url == "https://example.com/aurora-pack.png"
    assert pack.species_tags == ["wolf", "fox"]
    assert pack.max_size == 6
    assert pack.consensus_required is True
    assert pack.is_open is False
