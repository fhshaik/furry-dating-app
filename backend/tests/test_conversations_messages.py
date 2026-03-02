"""Tests for GET /api/conversations/{conversation_id}/messages endpoint."""

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
from app.models.pack_join_request import PackJoinRequest  # noqa: F401
from app.models.user import User


@pytest.fixture()
async def db_session():
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


async def _create_conversation(session: AsyncSession) -> Conversation:
    conv = Conversation(type=ConversationType.DIRECT)
    session.add(conv)
    await session.commit()
    await session.refresh(conv)
    return conv


async def _add_member(session: AsyncSession, conversation_id: int, user_id: int) -> None:
    session.add(ConversationMember(conversation_id=conversation_id, user_id=user_id))
    await session.commit()


async def _create_message(
    session: AsyncSession,
    conversation_id: int,
    sender_id: int,
    content: str,
    sent_at: datetime,
) -> Message:
    msg = Message(
        conversation_id=conversation_id,
        sender_id=sender_id,
        content=content,
        sent_at=sent_at,
    )
    session.add(msg)
    await session.commit()
    await session.refresh(msg)
    return msg


def test_list_messages_requires_auth():
    with TestClient(app, follow_redirects=False) as client:
        response = client.get("/api/conversations/1/messages")
    assert response.status_code == 401


async def test_list_messages_conversation_not_found(db_session: AsyncSession):
    user = await _create_user(db_session, "msg-noconv", "NoConv")

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app, follow_redirects=False) as client:
            response = client.get("/api/conversations/9999/messages")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 404


async def test_list_messages_not_member_returns_403(db_session: AsyncSession):
    user = await _create_user(db_session, "msg-nonmember", "NonMember")
    other = await _create_user(db_session, "msg-owner", "Owner")
    conv = await _create_conversation(db_session)
    await _add_member(db_session, conv.id, other.id)

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app, follow_redirects=False) as client:
            response = client.get(f"/api/conversations/{conv.id}/messages")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 403


async def test_list_messages_empty(db_session: AsyncSession):
    user = await _create_user(db_session, "msg-empty", "Empty")
    conv = await _create_conversation(db_session)
    await _add_member(db_session, conv.id, user.id)

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app, follow_redirects=False) as client:
            response = client.get(f"/api/conversations/{conv.id}/messages")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    assert response.json() == []


async def test_list_messages_returns_newest_first(db_session: AsyncSession):
    user = await _create_user(db_session, "msg-order", "Order")
    conv = await _create_conversation(db_session)
    await _add_member(db_session, conv.id, user.id)

    msg1 = await _create_message(db_session, conv.id, user.id, "first", datetime(2025, 1, 1, 10, 0, 0))
    msg2 = await _create_message(db_session, conv.id, user.id, "second", datetime(2025, 1, 1, 11, 0, 0))
    msg3 = await _create_message(db_session, conv.id, user.id, "third", datetime(2025, 1, 1, 12, 0, 0))

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app, follow_redirects=False) as client:
            response = client.get(f"/api/conversations/{conv.id}/messages")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert [m["id"] for m in data] == [msg3.id, msg2.id, msg1.id]
    assert [m["content"] for m in data] == ["third", "second", "first"]


async def test_list_messages_returns_correct_fields(db_session: AsyncSession):
    user = await _create_user(db_session, "msg-fields", "Fields")
    conv = await _create_conversation(db_session)
    await _add_member(db_session, conv.id, user.id)
    msg = await _create_message(db_session, conv.id, user.id, "hello", datetime(2025, 6, 1, 9, 0, 0))

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app, follow_redirects=False) as client:
            response = client.get(f"/api/conversations/{conv.id}/messages")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    item = data[0]
    assert item["id"] == msg.id
    assert item["conversation_id"] == conv.id
    assert item["sender_id"] == user.id
    assert item["content"] == "hello"
    assert item["is_read"] is False


async def test_list_messages_only_returns_messages_from_that_conversation(db_session: AsyncSession):
    user = await _create_user(db_session, "msg-isolation", "Isolation")
    conv1 = await _create_conversation(db_session)
    conv2 = await _create_conversation(db_session)
    await _add_member(db_session, conv1.id, user.id)
    await _add_member(db_session, conv2.id, user.id)

    msg_in = await _create_message(db_session, conv1.id, user.id, "in conv1", datetime(2025, 1, 1))
    await _create_message(db_session, conv2.id, user.id, "in conv2", datetime(2025, 1, 2))

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app, follow_redirects=False) as client:
            response = client.get(f"/api/conversations/{conv1.id}/messages")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == msg_in.id


async def test_list_messages_limit_param(db_session: AsyncSession):
    user = await _create_user(db_session, "msg-limit", "Limit")
    conv = await _create_conversation(db_session)
    await _add_member(db_session, conv.id, user.id)

    for i in range(5):
        await _create_message(db_session, conv.id, user.id, f"msg{i}", datetime(2025, 1, i + 1))

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app, follow_redirects=False) as client:
            response = client.get(f"/api/conversations/{conv.id}/messages?limit=3")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    assert len(response.json()) == 3


async def test_list_messages_before_id_pagination(db_session: AsyncSession):
    user = await _create_user(db_session, "msg-cursor", "Cursor")
    conv = await _create_conversation(db_session)
    await _add_member(db_session, conv.id, user.id)

    msg1 = await _create_message(db_session, conv.id, user.id, "msg1", datetime(2025, 1, 1))
    msg2 = await _create_message(db_session, conv.id, user.id, "msg2", datetime(2025, 1, 2))
    msg3 = await _create_message(db_session, conv.id, user.id, "msg3", datetime(2025, 1, 3))
    msg4 = await _create_message(db_session, conv.id, user.id, "msg4", datetime(2025, 1, 4))

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app, follow_redirects=False) as client:
            # First page: newest 2
            response = client.get(f"/api/conversations/{conv.id}/messages?limit=2")
            assert response.status_code == 200
            page1 = response.json()
            assert [m["id"] for m in page1] == [msg4.id, msg3.id]

            # Second page: before msg3
            response = client.get(
                f"/api/conversations/{conv.id}/messages?limit=2&before_id={msg3.id}"
            )
            assert response.status_code == 200
            page2 = response.json()
            assert [m["id"] for m in page2] == [msg2.id, msg1.id]
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)


async def test_list_messages_before_id_nonexistent_returns_all(db_session: AsyncSession):
    user = await _create_user(db_session, "msg-badcursor", "BadCursor")
    conv = await _create_conversation(db_session)
    await _add_member(db_session, conv.id, user.id)
    await _create_message(db_session, conv.id, user.id, "hello", datetime(2025, 1, 1))

    app.dependency_overrides[get_current_user] = _override_current_user(user)
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app, follow_redirects=False) as client:
            response = client.get(f"/api/conversations/{conv.id}/messages?before_id=9999")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    assert len(response.json()) == 1
