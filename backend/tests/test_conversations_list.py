"""Tests for GET /api/conversations endpoint."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.deps import get_current_user
from app.database import Base, get_db
from app.main import app
from app.models.conversation import Conversation, ConversationType
from app.models.conversation_member import ConversationMember
from app.models.message import Message
from app.models.pack import Pack
from app.models.pack_join_request import PackJoinRequest  # noqa: F401
from app.models.user import User


@pytest.fixture()
async def conv_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


def _override_current_user(user: User):
    async def _override():
        return user

    return _override


def _override_db(session: AsyncSession):
    async def _db():
        yield session

    return _db


async def _create_user(session: AsyncSession, oauth_id: str, display_name: str) -> User:
    user = User(
        oauth_provider="google",
        oauth_id=oauth_id,
        email=f"{oauth_id}@example.com",
        display_name=display_name,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


def test_list_conversations_requires_auth():
    with TestClient(app, follow_redirects=False) as client:
        response = client.get("/api/conversations")
    assert response.status_code == 401


async def test_list_conversations_empty(conv_session: AsyncSession):
    user = await _create_user(conv_session, "conv-empty-user", "Empty")

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db(conv_session)
    try:
        with TestClient(app, follow_redirects=False) as client:
            response = client.get("/api/conversations")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    assert response.json() == []


async def test_list_conversations_returns_only_member_conversations(
    conv_session: AsyncSession,
):
    current_user = await _create_user(conv_session, "conv-current", "Current")
    other_user = await _create_user(conv_session, "conv-other", "Other")

    # Conversation current_user is a member of
    conv_mine = Conversation(type=ConversationType.DIRECT, created_at=datetime(2025, 3, 1))
    conv_session.add(conv_mine)
    await conv_session.flush()
    conv_session.add(ConversationMember(conversation_id=conv_mine.id, user_id=current_user.id))
    conv_session.add(ConversationMember(conversation_id=conv_mine.id, user_id=other_user.id))

    # Conversation current_user is NOT a member of
    conv_other = Conversation(type=ConversationType.DIRECT, created_at=datetime(2025, 3, 2))
    conv_session.add(conv_other)
    await conv_session.flush()
    conv_session.add(ConversationMember(conversation_id=conv_other.id, user_id=other_user.id))

    await conv_session.commit()

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(conv_session)
    try:
        with TestClient(app, follow_redirects=False) as client:
            response = client.get("/api/conversations")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == conv_mine.id
    assert data[0]["type"] == "direct"
    assert data[0]["pack_id"] is None


async def test_list_conversations_ordered_by_created_at_desc(conv_session: AsyncSession):
    user = await _create_user(conv_session, "conv-order-user", "OrderUser")

    conv_old = Conversation(type=ConversationType.DIRECT, created_at=datetime(2025, 1, 1))
    conv_new = Conversation(type=ConversationType.DIRECT, created_at=datetime(2025, 6, 1))
    conv_session.add_all([conv_old, conv_new])
    await conv_session.flush()

    conv_session.add(ConversationMember(conversation_id=conv_old.id, user_id=user.id))
    conv_session.add(ConversationMember(conversation_id=conv_new.id, user_id=user.id))
    await conv_session.commit()

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db(conv_session)
    try:
        with TestClient(app, follow_redirects=False) as client:
            response = client.get("/api/conversations")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["id"] == conv_new.id
    assert data[1]["id"] == conv_old.id


async def test_list_conversations_includes_pack_conversation(conv_session: AsyncSession):
    user = await _create_user(conv_session, "conv-pack-user", "PackUser")

    pack = Pack(creator_id=user.id, name="My Pack")
    conv_session.add(pack)
    await conv_session.flush()

    conv = Conversation(type=ConversationType.PACK, pack_id=pack.id)
    conv_session.add(conv)
    await conv_session.flush()
    conv_session.add(ConversationMember(conversation_id=conv.id, user_id=user.id))
    await conv_session.commit()

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db(conv_session)
    try:
        with TestClient(app, follow_redirects=False) as client:
            response = client.get("/api/conversations")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["type"] == "pack"
    assert data[0]["pack_id"] == pack.id
    assert data[0]["unread_count"] == 0


async def test_list_conversations_includes_unread_count_for_current_user(conv_session: AsyncSession):
    current_user = await _create_user(conv_session, "conv-unread-current", "Current")
    other_user = await _create_user(conv_session, "conv-unread-other", "Other")

    conv = Conversation(type=ConversationType.DIRECT, created_at=datetime(2025, 3, 3))
    conv_session.add(conv)
    await conv_session.flush()
    conv_session.add(ConversationMember(conversation_id=conv.id, user_id=current_user.id))
    conv_session.add(ConversationMember(conversation_id=conv.id, user_id=other_user.id))
    await conv_session.flush()

    conv_session.add_all(
        [
            Message(
                conversation_id=conv.id,
                sender_id=other_user.id,
                content="Unread 1",
                is_read=False,
            ),
            Message(
                conversation_id=conv.id,
                sender_id=other_user.id,
                content="Unread 2",
                is_read=False,
            ),
            Message(
                conversation_id=conv.id,
                sender_id=other_user.id,
                content="Already read",
                is_read=True,
            ),
            Message(
                conversation_id=conv.id,
                sender_id=current_user.id,
                content="Mine should not count",
                is_read=False,
            ),
        ]
    )
    await conv_session.commit()

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(conv_session)
    try:
        with TestClient(app, follow_redirects=False) as client:
            response = client.get("/api/conversations")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["unread_count"] == 2
