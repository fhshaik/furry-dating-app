"""Tests for the Message ORM model."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.conversation import Conversation, ConversationType
from app.models.message import Message
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


def test_message_tablename():
    assert Message.__tablename__ == "messages"


def test_message_has_required_columns():
    column_names = set(Message.__table__.c.keys())
    assert "id" in column_names
    assert "conversation_id" in column_names
    assert "sender_id" in column_names
    assert "content" in column_names
    assert "sent_at" in column_names
    assert "is_read" in column_names


async def test_create_message(sqlite_session: AsyncSession):
    user = User(oauth_provider="google", oauth_id="msg-user-1", display_name="Sender")
    sqlite_session.add(user)
    await sqlite_session.commit()

    conv = Conversation(type=ConversationType.DIRECT)
    sqlite_session.add(conv)
    await sqlite_session.commit()

    msg = Message(conversation_id=conv.id, sender_id=user.id, content="Hello!")
    sqlite_session.add(msg)
    await sqlite_session.commit()
    await sqlite_session.refresh(msg)

    assert msg.id is not None
    assert msg.conversation_id == conv.id
    assert msg.sender_id == user.id
    assert msg.content == "Hello!"
    assert msg.sent_at is not None
    assert msg.is_read is False


async def test_is_read_defaults_to_false(sqlite_session: AsyncSession):
    user = User(oauth_provider="google", oauth_id="msg-user-2", display_name="Sender2")
    sqlite_session.add(user)
    await sqlite_session.commit()

    conv = Conversation(type=ConversationType.DIRECT)
    sqlite_session.add(conv)
    await sqlite_session.commit()

    msg = Message(conversation_id=conv.id, sender_id=user.id, content="Test")
    sqlite_session.add(msg)
    await sqlite_session.commit()
    await sqlite_session.refresh(msg)

    assert msg.is_read is False


async def test_is_read_can_be_set_true(sqlite_session: AsyncSession):
    user = User(oauth_provider="google", oauth_id="msg-user-3", display_name="Sender3")
    sqlite_session.add(user)
    await sqlite_session.commit()

    conv = Conversation(type=ConversationType.DIRECT)
    sqlite_session.add(conv)
    await sqlite_session.commit()

    msg = Message(conversation_id=conv.id, sender_id=user.id, content="Read me", is_read=True)
    sqlite_session.add(msg)
    await sqlite_session.commit()
    await sqlite_session.refresh(msg)

    assert msg.is_read is True
