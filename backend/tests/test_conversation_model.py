"""Tests for the Conversation ORM model."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.conversation import Conversation, ConversationType
from app.models.pack import Pack
from app.models.pack_join_request import PackJoinRequest  # noqa: F401
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


def test_conversation_tablename():
    assert Conversation.__tablename__ == "conversations"


def test_conversation_has_required_columns():
    column_names = set(Conversation.__table__.c.keys())
    assert "id" in column_names
    assert "type" in column_names
    assert "pack_id" in column_names
    assert "created_at" in column_names


def test_conversation_type_values():
    assert ConversationType.DIRECT == "direct"
    assert ConversationType.PACK == "pack"


async def test_create_direct_conversation(sqlite_session: AsyncSession):
    conv = Conversation(type=ConversationType.DIRECT)
    sqlite_session.add(conv)
    await sqlite_session.commit()
    await sqlite_session.refresh(conv)

    assert conv.id is not None
    assert conv.type == ConversationType.DIRECT
    assert conv.pack_id is None
    assert conv.created_at is not None


async def test_create_pack_conversation(sqlite_session: AsyncSession):
    user = User(oauth_provider="google", oauth_id="conv-pack-user", display_name="Packster")
    sqlite_session.add(user)
    await sqlite_session.commit()

    pack = Pack(creator_id=user.id, name="Test Pack")
    sqlite_session.add(pack)
    await sqlite_session.commit()

    conv = Conversation(type=ConversationType.PACK, pack_id=pack.id)
    sqlite_session.add(conv)
    await sqlite_session.commit()
    await sqlite_session.refresh(conv)

    assert conv.id is not None
    assert conv.type == ConversationType.PACK
    assert conv.pack_id == pack.id
    assert conv.created_at is not None


async def test_pack_id_is_optional(sqlite_session: AsyncSession):
    conv = Conversation(type=ConversationType.DIRECT, pack_id=None)
    sqlite_session.add(conv)
    await sqlite_session.commit()
    await sqlite_session.refresh(conv)

    assert conv.pack_id is None
