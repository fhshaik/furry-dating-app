"""Tests for WS /ws/chat/{conversation_id} WebSocket endpoint."""

from contextlib import suppress

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from starlette.websockets import WebSocketDisconnect

from app.core.security import create_access_token
from app.database import Base, get_db
from app.main import app
from app.models.conversation import Conversation, ConversationType
from app.models.conversation_member import ConversationMember
from app.models.message import Message
from app.models.notification import Notification
from app.models.pack_join_request import PackJoinRequest  # noqa: F401
from app.models.user import User
from app.routers.ws import get_ws_user, manager


@pytest.fixture(autouse=True)
def clear_ws_manager():
    """Reset ConnectionManager state between tests."""
    manager._connections.clear()
    manager._user_connections.clear()
    yield
    manager._connections.clear()
    manager._user_connections.clear()


@pytest.fixture()
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
    finally:
        with suppress(OperationalError):
            await session.close()
        await engine.dispose()


def _override_ws_user(user: User | None):
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


# ---------------------------------------------------------------------------
# Authentication and authorization rejection tests
# ---------------------------------------------------------------------------


async def test_ws_chat_rejects_unauthenticated(db_session: AsyncSession):
    app.dependency_overrides[get_ws_user] = _override_ws_user(None)
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            with pytest.raises(WebSocketDisconnect) as exc_info:
                with client.websocket_connect("/ws/chat/1"):
                    pass
        assert exc_info.value.code == 4001
    finally:
        app.dependency_overrides.pop(get_ws_user, None)
        app.dependency_overrides.pop(get_db, None)


async def test_ws_chat_rejects_nonexistent_conversation(db_session: AsyncSession):
    user = await _create_user(db_session, "ws-no-conv", "NoConv")

    app.dependency_overrides[get_ws_user] = _override_ws_user(user)
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            with pytest.raises(WebSocketDisconnect) as exc_info:
                with client.websocket_connect("/ws/chat/9999"):
                    pass
        assert exc_info.value.code == 4004
    finally:
        app.dependency_overrides.pop(get_ws_user, None)
        app.dependency_overrides.pop(get_db, None)


async def test_ws_chat_rejects_non_member(db_session: AsyncSession):
    user = await _create_user(db_session, "ws-non-member", "NonMember")
    conv = await _create_conversation(db_session)

    app.dependency_overrides[get_ws_user] = _override_ws_user(user)
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            with pytest.raises(WebSocketDisconnect) as exc_info:
                with client.websocket_connect(f"/ws/chat/{conv.id}"):
                    pass
        assert exc_info.value.code == 4003
    finally:
        app.dependency_overrides.pop(get_ws_user, None)
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------


async def test_ws_chat_send_message(db_session: AsyncSession):
    user = await _create_user(db_session, "ws-sender", "Sender")
    conv = await _create_conversation(db_session)
    await _add_member(db_session, conv.id, user.id)

    app.dependency_overrides[get_ws_user] = _override_ws_user(user)
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            with client.websocket_connect(f"/ws/chat/{conv.id}") as ws:
                ws.send_json({"content": "hello world"})
                data = ws.receive_json()
    finally:
        app.dependency_overrides.pop(get_ws_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert data["content"] == "hello world"
    assert data["sender_id"] == user.id
    assert data["conversation_id"] == conv.id
    assert data["is_read"] is False
    assert "id" in data
    assert "sent_at" in data


async def test_ws_chat_ignores_empty_content(db_session: AsyncSession):
    user = await _create_user(db_session, "ws-empty", "Empty")
    conv = await _create_conversation(db_session)
    await _add_member(db_session, conv.id, user.id)

    app.dependency_overrides[get_ws_user] = _override_ws_user(user)
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            with client.websocket_connect(f"/ws/chat/{conv.id}") as ws:
                ws.send_json({"content": "   "})
                # Send a real message right after to confirm the server is still running
                ws.send_json({"content": "real message"})
                data = ws.receive_json()
    finally:
        app.dependency_overrides.pop(get_ws_user, None)
        app.dependency_overrides.pop(get_db, None)

    # Only the real message should be broadcast
    assert data["content"] == "real message"


async def test_ws_chat_trims_message_content(db_session: AsyncSession):
    sender = await _create_user(db_session, "ws-trim-sender", "Sender")
    conv = await _create_conversation(db_session)
    await _add_member(db_session, conv.id, sender.id)

    app.dependency_overrides[get_ws_user] = _override_ws_user(sender)
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            with client.websocket_connect(f"/ws/chat/{conv.id}") as ws:
                ws.send_json({"content": "  hello world  "})
                data = ws.receive_json()
    finally:
        app.dependency_overrides.pop(get_ws_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert data["content"] == "hello world"


async def test_ws_chat_broadcast_to_multiple_clients(db_session: AsyncSession):
    sender = await _create_user(db_session, "ws-bcast-sender", "Sender")
    receiver = await _create_user(db_session, "ws-bcast-receiver", "Receiver")
    conv = await _create_conversation(db_session)
    await _add_member(db_session, conv.id, sender.id)
    await _add_member(db_session, conv.id, receiver.id)

    app.dependency_overrides[get_db] = _override_db(db_session)

    received_by_sender = None
    received_by_receiver = None

    try:
        with TestClient(app) as client:
            app.dependency_overrides[get_ws_user] = _override_ws_user(sender)
            with client.websocket_connect(f"/ws/chat/{conv.id}") as ws_sender:
                app.dependency_overrides[get_ws_user] = _override_ws_user(receiver)
                with client.websocket_connect(f"/ws/chat/{conv.id}") as ws_receiver:
                    # Reset to sender for the send operation
                    app.dependency_overrides[get_ws_user] = _override_ws_user(sender)
                    ws_sender.send_json({"content": "broadcast test"})
                    received_by_sender = ws_sender.receive_json()
                    received_by_receiver = ws_receiver.receive_json()
    finally:
        app.dependency_overrides.pop(get_ws_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert received_by_sender["content"] == "broadcast test"
    assert received_by_receiver["content"] == "broadcast test"
    assert received_by_sender["sender_id"] == sender.id
    assert received_by_receiver["sender_id"] == sender.id


async def test_ws_send_creates_notification_for_offline_recipient(db_session: AsyncSession):
    sender = await _create_user(db_session, "ws-notify-sender", "Sender")
    receiver = await _create_user(db_session, "ws-notify-receiver", "Receiver")
    conv = await _create_conversation(db_session)
    await _add_member(db_session, conv.id, sender.id)
    await _add_member(db_session, conv.id, receiver.id)

    app.dependency_overrides[get_ws_user] = _override_ws_user(sender)
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            with client.websocket_connect(f"/ws/chat/{conv.id}") as ws:
                ws.send_json({"content": "offline ping"})
                data = ws.receive_json()
    finally:
        app.dependency_overrides.pop(get_ws_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert data["content"] == "offline ping"
    notifications = (
        await db_session.execute(select(Notification).order_by(Notification.user_id.asc()))
    ).scalars().all()

    assert len(notifications) == 1
    assert notifications[0].user_id == receiver.id
    assert notifications[0].type == "message_received"
    assert notifications[0].payload["conversation_id"] == conv.id
    assert notifications[0].payload["sender_id"] == sender.id
    assert notifications[0].payload["message_id"] == data["id"]


async def test_ws_send_does_not_notify_connected_recipient(db_session: AsyncSession):
    sender = await _create_user(db_session, "ws-live-sender", "Sender")
    receiver = await _create_user(db_session, "ws-live-receiver", "Receiver")
    conv = await _create_conversation(db_session)
    await _add_member(db_session, conv.id, sender.id)
    await _add_member(db_session, conv.id, receiver.id)

    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            app.dependency_overrides[get_ws_user] = _override_ws_user(sender)
            with client.websocket_connect(f"/ws/chat/{conv.id}") as ws_sender:
                app.dependency_overrides[get_ws_user] = _override_ws_user(receiver)
                with client.websocket_connect(f"/ws/chat/{conv.id}") as ws_receiver:
                    app.dependency_overrides[get_ws_user] = _override_ws_user(sender)
                    ws_sender.send_json({"content": "live ping"})
                    ws_sender.receive_json()
                    ws_receiver.receive_json()
                    ws_sender.receive_json()
                    ws_receiver.receive_json()
    finally:
        app.dependency_overrides.pop(get_ws_user, None)
        app.dependency_overrides.pop(get_db, None)

    notifications = (await db_session.execute(select(Notification))).scalars().all()
    assert notifications == []


# ---------------------------------------------------------------------------
# JWT query-param authentication tests
# ---------------------------------------------------------------------------


async def test_ws_auth_via_query_param_valid_token(db_session: AsyncSession):
    """A valid JWT passed as ?token= should authenticate the connection."""
    user = await _create_user(db_session, "ws-qp-auth", "QPAuth")
    conv = await _create_conversation(db_session)
    await _add_member(db_session, conv.id, user.id)

    token = create_access_token(user.id)
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            with client.websocket_connect(f"/ws/chat/{conv.id}?token={token}") as ws:
                ws.send_json({"content": "query param auth works"})
                data = ws.receive_json()
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert data["content"] == "query param auth works"
    assert data["sender_id"] == user.id


async def test_ws_auth_via_cookie_still_works(db_session: AsyncSession):
    """A valid JWT passed as a cookie should still authenticate the connection."""
    user = await _create_user(db_session, "ws-cookie-auth", "CookieAuth")
    conv = await _create_conversation(db_session)
    await _add_member(db_session, conv.id, user.id)

    token = create_access_token(user.id)
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app, cookies={"access_token": token}) as client:
            with client.websocket_connect(f"/ws/chat/{conv.id}") as ws:
                ws.send_json({"content": "cookie auth works"})
                data = ws.receive_json()
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert data["content"] == "cookie auth works"
    assert data["sender_id"] == user.id


async def test_ws_auth_query_param_invalid_token_rejected(db_session: AsyncSession):
    """An invalid JWT in ?token= should close the connection with code 4001."""
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            with pytest.raises(WebSocketDisconnect) as exc_info:
                with client.websocket_connect("/ws/chat/1?token=not.a.valid.jwt"):
                    pass
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert exc_info.value.code == 4001


async def test_ws_auth_no_token_rejected(db_session: AsyncSession):
    """No token (no cookie, no query param) should close with code 4001."""
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            with pytest.raises(WebSocketDisconnect) as exc_info:
                with client.websocket_connect("/ws/chat/1"):
                    pass
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert exc_info.value.code == 4001


async def test_ws_auth_cookie_takes_precedence_over_query_param(db_session: AsyncSession):
    """When both cookie and query param are present, the cookie user is authenticated."""
    cookie_user = await _create_user(db_session, "ws-cookie-user", "CookieUser")
    conv = await _create_conversation(db_session)
    await _add_member(db_session, conv.id, cookie_user.id)

    cookie_token = create_access_token(cookie_user.id)
    # A token for a non-existent user in the query param
    bogus_token = create_access_token(99999)

    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app, cookies={"access_token": cookie_token}) as client:
            with client.websocket_connect(f"/ws/chat/{conv.id}?token={bogus_token}") as ws:
                ws.send_json({"content": "cookie wins"})
                data = ws.receive_json()
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert data["content"] == "cookie wins"
    assert data["sender_id"] == cookie_user.id


# ---------------------------------------------------------------------------
# Broadcast correctness and cleanup tests
# ---------------------------------------------------------------------------


async def test_ws_broadcast_to_three_clients(db_session: AsyncSession):
    """A message is broadcast to all three connected clients."""
    users = []
    for i in range(3):
        u = await _create_user(db_session, f"ws-3c-user-{i}", f"User{i}")
        users.append(u)
    conv = await _create_conversation(db_session)
    for u in users:
        await _add_member(db_session, conv.id, u.id)

    app.dependency_overrides[get_db] = _override_db(db_session)
    received = []
    try:
        with TestClient(app) as client:
            app.dependency_overrides[get_ws_user] = _override_ws_user(users[0])
            with client.websocket_connect(f"/ws/chat/{conv.id}") as ws0:
                app.dependency_overrides[get_ws_user] = _override_ws_user(users[1])
                with client.websocket_connect(f"/ws/chat/{conv.id}") as ws1:
                    app.dependency_overrides[get_ws_user] = _override_ws_user(users[2])
                    with client.websocket_connect(f"/ws/chat/{conv.id}") as ws2:
                        app.dependency_overrides[get_ws_user] = _override_ws_user(users[0])
                        ws0.send_json({"content": "three clients"})
                        received.append(ws0.receive_json())
                        received.append(ws1.receive_json())
                        received.append(ws2.receive_json())
    finally:
        app.dependency_overrides.pop(get_ws_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert len(received) == 3
    for msg in received:
        assert msg["content"] == "three clients"
        assert msg["sender_id"] == users[0].id


async def test_ws_disconnect_removes_connection_from_manager(db_session: AsyncSession):
    """After a client disconnects the manager no longer holds that connection."""
    user = await _create_user(db_session, "ws-cleanup", "Cleanup")
    conv = await _create_conversation(db_session)
    await _add_member(db_session, conv.id, user.id)

    app.dependency_overrides[get_ws_user] = _override_ws_user(user)
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            with client.websocket_connect(f"/ws/chat/{conv.id}"):
                assert conv.id in manager._connections
                assert len(manager._connections[conv.id]) == 1
        # After the context manager exits the connection is closed
        assert conv.id not in manager._connections
    finally:
        app.dependency_overrides.pop(get_ws_user, None)
        app.dependency_overrides.pop(get_db, None)


async def test_ws_broadcast_skips_dead_connection(db_session: AsyncSession):
    """Broadcast completes for all live clients even if one connection is broken."""
    sender = await _create_user(db_session, "ws-dead-sender", "Sender")
    receiver = await _create_user(db_session, "ws-dead-receiver", "Receiver")
    conv = await _create_conversation(db_session)
    await _add_member(db_session, conv.id, sender.id)
    await _add_member(db_session, conv.id, receiver.id)

    app.dependency_overrides[get_db] = _override_db(db_session)
    received_by_receiver = None
    try:
        with TestClient(app) as client:
            app.dependency_overrides[get_ws_user] = _override_ws_user(sender)
            with client.websocket_connect(f"/ws/chat/{conv.id}") as ws_sender:
                app.dependency_overrides[get_ws_user] = _override_ws_user(receiver)
                with client.websocket_connect(f"/ws/chat/{conv.id}") as ws_receiver:
                    # Inject a dead placeholder into the manager for the conversation
                    # (simulates a connection that closed without going through disconnect)
                    from unittest.mock import AsyncMock, MagicMock

                    dead_ws = MagicMock()
                    dead_ws.send_json = AsyncMock(side_effect=RuntimeError("broken pipe"))
                    manager._connections[conv.id].insert(0, dead_ws)

                    app.dependency_overrides[get_ws_user] = _override_ws_user(sender)
                    ws_sender.send_json({"content": "skip dead"})
                    received_by_receiver = ws_receiver.receive_json()
    finally:
        app.dependency_overrides.pop(get_ws_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert received_by_receiver["content"] == "skip dead"


# ---------------------------------------------------------------------------
# DB persistence tests
# ---------------------------------------------------------------------------


async def test_ws_send_persists_message_to_db(db_session: AsyncSession):
    """Sending a message over WebSocket persists it to the messages table."""
    user = await _create_user(db_session, "ws-persist", "Persist")
    conv = await _create_conversation(db_session)
    await _add_member(db_session, conv.id, user.id)

    app.dependency_overrides[get_ws_user] = _override_ws_user(user)
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            with client.websocket_connect(f"/ws/chat/{conv.id}") as ws:
                ws.send_json({"content": "persisted message"})
                data = ws.receive_json()
    finally:
        app.dependency_overrides.pop(get_ws_user, None)
        app.dependency_overrides.pop(get_db, None)

    # Verify DB persistence
    result = await db_session.scalar(select(Message).where(Message.id == data["id"]))
    assert result is not None
    assert result.content == "persisted message"
    assert result.sender_id == user.id
    assert result.conversation_id == conv.id
    assert result.is_read is False
    assert result.sent_at is not None


async def test_ws_send_multiple_messages_all_persisted(db_session: AsyncSession):
    """All messages sent in a session are each individually persisted to the DB."""
    user = await _create_user(db_session, "ws-multi-persist", "MultiPersist")
    conv = await _create_conversation(db_session)
    await _add_member(db_session, conv.id, user.id)

    app.dependency_overrides[get_ws_user] = _override_ws_user(user)
    app.dependency_overrides[get_db] = _override_db(db_session)
    received = []
    try:
        with TestClient(app) as client:
            with client.websocket_connect(f"/ws/chat/{conv.id}") as ws:
                for text in ("first", "second", "third"):
                    ws.send_json({"content": text})
                    received.append(ws.receive_json())
    finally:
        app.dependency_overrides.pop(get_ws_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert len(received) == 3
    for msg_data in received:
        row = await db_session.scalar(select(Message).where(Message.id == msg_data["id"]))
        assert row is not None
        assert row.content == msg_data["content"]
        assert row.sender_id == user.id
        assert row.conversation_id == conv.id


async def test_ws_empty_content_not_persisted(db_session: AsyncSession):
    """Whitespace-only messages are not persisted to the DB."""
    user = await _create_user(db_session, "ws-no-persist", "NoPersist")
    conv = await _create_conversation(db_session)
    await _add_member(db_session, conv.id, user.id)

    app.dependency_overrides[get_ws_user] = _override_ws_user(user)
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            with client.websocket_connect(f"/ws/chat/{conv.id}") as ws:
                ws.send_json({"content": "   "})
                # Send a real message so the server stays alive long enough to process
                ws.send_json({"content": "real"})
                ws.receive_json()
    finally:
        app.dependency_overrides.pop(get_ws_user, None)
        app.dependency_overrides.pop(get_db, None)

    rows = (await db_session.scalars(select(Message).where(Message.conversation_id == conv.id))).all()
    assert len(rows) == 1
    assert rows[0].content == "real"


async def test_ws_persisted_message_id_matches_broadcast(db_session: AsyncSession):
    """The message ID in the broadcast payload matches the DB row ID."""
    user = await _create_user(db_session, "ws-id-match", "IdMatch")
    conv = await _create_conversation(db_session)
    await _add_member(db_session, conv.id, user.id)

    app.dependency_overrides[get_ws_user] = _override_ws_user(user)
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            with client.websocket_connect(f"/ws/chat/{conv.id}") as ws:
                ws.send_json({"content": "id check"})
                data = ws.receive_json()
    finally:
        app.dependency_overrides.pop(get_ws_user, None)
        app.dependency_overrides.pop(get_db, None)

    row = await db_session.scalar(select(Message).where(Message.id == data["id"]))
    assert row is not None
    assert row.id == data["id"]
    assert row.content == "id check"


# ---------------------------------------------------------------------------
# Read receipt tests
# ---------------------------------------------------------------------------


async def _create_message(
    session: AsyncSession,
    conversation_id: int,
    sender_id: int,
    content: str,
    is_read: bool = False,
) -> Message:
    msg = Message(
        conversation_id=conversation_id,
        sender_id=sender_id,
        content=content,
        is_read=is_read,
    )
    session.add(msg)
    await session.commit()
    await session.refresh(msg)
    return msg


async def test_ws_connect_marks_existing_unread_messages_read(db_session: AsyncSession):
    """On connect, unread messages from other users are marked as read in the DB."""
    sender = await _create_user(db_session, "rr-sender", "Sender")
    reader = await _create_user(db_session, "rr-reader", "Reader")
    conv = await _create_conversation(db_session)
    await _add_member(db_session, conv.id, sender.id)
    await _add_member(db_session, conv.id, reader.id)

    # Sender pre-creates two unread messages
    msg1 = await _create_message(db_session, conv.id, sender.id, "hello")
    msg2 = await _create_message(db_session, conv.id, sender.id, "world")

    app.dependency_overrides[get_ws_user] = _override_ws_user(reader)
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            with client.websocket_connect(f"/ws/chat/{conv.id}") as ws:
                # Receive the read_receipt broadcast triggered on connect
                receipt = ws.receive_json()
    finally:
        app.dependency_overrides.pop(get_ws_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert receipt["type"] == "read_receipt"
    assert set(receipt["message_ids"]) == {msg1.id, msg2.id}
    assert receipt["reader_id"] == reader.id

    # Verify DB rows are updated
    await db_session.refresh(msg1)
    await db_session.refresh(msg2)
    assert msg1.is_read is True
    assert msg2.is_read is True


async def test_ws_connect_does_not_mark_own_messages_read(db_session: AsyncSession):
    """On connect, messages the user sent themselves are not marked as read."""
    user = await _create_user(db_session, "rr-own", "Own")
    conv = await _create_conversation(db_session)
    await _add_member(db_session, conv.id, user.id)

    own_msg = await _create_message(db_session, conv.id, user.id, "my own message")

    app.dependency_overrides[get_ws_user] = _override_ws_user(user)
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            with client.websocket_connect(f"/ws/chat/{conv.id}") as ws:
                # Send a real message so we can confirm no extra events were sent first
                ws.send_json({"content": "ping"})
                data = ws.receive_json()
    finally:
        app.dependency_overrides.pop(get_ws_user, None)
        app.dependency_overrides.pop(get_db, None)

    # The only broadcast received is the message, not a read_receipt
    assert data["type"] == "message"
    assert data["content"] == "ping"

    await db_session.refresh(own_msg)
    assert own_msg.is_read is False


async def test_ws_connect_no_read_receipt_when_no_unread_messages(db_session: AsyncSession):
    """No read_receipt event is broadcast when there are no unread messages on connect."""
    user = await _create_user(db_session, "rr-none", "None")
    conv = await _create_conversation(db_session)
    await _add_member(db_session, conv.id, user.id)

    app.dependency_overrides[get_ws_user] = _override_ws_user(user)
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            with client.websocket_connect(f"/ws/chat/{conv.id}") as ws:
                ws.send_json({"content": "first message"})
                data = ws.receive_json()
    finally:
        app.dependency_overrides.pop(get_ws_user, None)
        app.dependency_overrides.pop(get_db, None)

    # The first received event is the message itself, not a read_receipt
    assert data["type"] == "message"


async def test_ws_already_read_messages_not_re_broadcast(db_session: AsyncSession):
    """Messages already marked read do not trigger a read_receipt event on connect."""
    sender = await _create_user(db_session, "rr-already-sender", "Sender")
    reader = await _create_user(db_session, "rr-already-reader", "Reader")
    conv = await _create_conversation(db_session)
    await _add_member(db_session, conv.id, sender.id)
    await _add_member(db_session, conv.id, reader.id)

    # Pre-create a message that's already read
    await _create_message(db_session, conv.id, sender.id, "already read", is_read=True)

    app.dependency_overrides[get_ws_user] = _override_ws_user(reader)
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            with client.websocket_connect(f"/ws/chat/{conv.id}") as ws:
                ws.send_json({"content": "ping"})
                data = ws.receive_json()
    finally:
        app.dependency_overrides.pop(get_ws_user, None)
        app.dependency_overrides.pop(get_db, None)

    # No read_receipt; first received event is the sent message
    assert data["type"] == "message"


async def test_ws_new_message_marked_read_when_recipient_connected(db_session: AsyncSession):
    """A new message is immediately marked as read when the recipient is already connected."""
    sender = await _create_user(db_session, "rr-live-sender", "Sender")
    receiver = await _create_user(db_session, "rr-live-receiver", "Receiver")
    conv = await _create_conversation(db_session)
    await _add_member(db_session, conv.id, sender.id)
    await _add_member(db_session, conv.id, receiver.id)

    app.dependency_overrides[get_db] = _override_db(db_session)
    broadcast_to_receiver = None
    try:
        with TestClient(app) as client:
            app.dependency_overrides[get_ws_user] = _override_ws_user(receiver)
            with client.websocket_connect(f"/ws/chat/{conv.id}") as ws_receiver:
                app.dependency_overrides[get_ws_user] = _override_ws_user(sender)
                with client.websocket_connect(f"/ws/chat/{conv.id}") as ws_sender:
                    ws_sender.send_json({"content": "live message"})
                    # Both connections get the message broadcast then a read_receipt
                    broadcast_to_receiver = ws_receiver.receive_json()
                    ws_receiver.receive_json()  # drain read_receipt
                    ws_sender.receive_json()  # drain sender's message copy
                    ws_sender.receive_json()  # drain sender's read_receipt copy
    finally:
        app.dependency_overrides.pop(get_ws_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert broadcast_to_receiver["type"] == "message"
    assert broadcast_to_receiver["content"] == "live message"
    assert broadcast_to_receiver["is_read"] is True

    # Confirm DB row is also updated
    row = await db_session.scalar(
        select(Message).where(Message.id == broadcast_to_receiver["id"])
    )
    assert row is not None
    assert row.is_read is True


async def test_ws_new_message_stays_unread_when_no_recipient_connected(db_session: AsyncSession):
    """A new message stays unread when only the sender is connected."""
    user = await _create_user(db_session, "rr-solo-sender", "SoloSender")
    conv = await _create_conversation(db_session)
    await _add_member(db_session, conv.id, user.id)

    app.dependency_overrides[get_ws_user] = _override_ws_user(user)
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            with client.websocket_connect(f"/ws/chat/{conv.id}") as ws:
                ws.send_json({"content": "solo message"})
                data = ws.receive_json()
    finally:
        app.dependency_overrides.pop(get_ws_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert data["type"] == "message"
    assert data["is_read"] is False

    row = await db_session.scalar(select(Message).where(Message.id == data["id"]))
    assert row is not None
    assert row.is_read is False


# ---------------------------------------------------------------------------
# reader_display_name in read_receipt tests
# ---------------------------------------------------------------------------


async def test_ws_read_receipt_on_connect_includes_reader_display_name(db_session: AsyncSession):
    """read_receipt broadcast on connect includes reader_display_name."""
    sender = await _create_user(db_session, "rdn-sender", "TheSender")
    reader = await _create_user(db_session, "rdn-reader", "TheReader")
    conv = await _create_conversation(db_session)
    await _add_member(db_session, conv.id, sender.id)
    await _add_member(db_session, conv.id, reader.id)

    await _create_message(db_session, conv.id, sender.id, "hello")

    app.dependency_overrides[get_ws_user] = _override_ws_user(reader)
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            with client.websocket_connect(f"/ws/chat/{conv.id}") as ws:
                receipt = ws.receive_json()
    finally:
        app.dependency_overrides.pop(get_ws_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert receipt["type"] == "read_receipt"
    assert receipt["reader_id"] == reader.id
    assert receipt["reader_display_name"] == reader.display_name


async def test_ws_read_receipt_broadcast_when_message_immediately_read(db_session: AsyncSession):
    """When a message is sent while recipient is connected a read_receipt is broadcast."""
    sender = await _create_user(db_session, "rdn-live-sender", "LiveSender")
    receiver = await _create_user(db_session, "rdn-live-receiver", "LiveReceiver")
    conv = await _create_conversation(db_session)
    await _add_member(db_session, conv.id, sender.id)
    await _add_member(db_session, conv.id, receiver.id)

    app.dependency_overrides[get_db] = _override_db(db_session)
    sender_events: list[dict] = []
    try:
        with TestClient(app) as client:
            app.dependency_overrides[get_ws_user] = _override_ws_user(receiver)
            with client.websocket_connect(f"/ws/chat/{conv.id}") as ws_receiver:
                app.dependency_overrides[get_ws_user] = _override_ws_user(sender)
                with client.websocket_connect(f"/ws/chat/{conv.id}") as ws_sender:
                    ws_sender.send_json({"content": "seen immediately"})
                    # Drain receiver's message copy
                    ws_receiver.receive_json()
                    # Drain receiver's read_receipt copy
                    ws_receiver.receive_json()
                    # Sender gets the message broadcast then the read_receipt
                    sender_events.append(ws_sender.receive_json())  # message
                    sender_events.append(ws_sender.receive_json())  # read_receipt
    finally:
        app.dependency_overrides.pop(get_ws_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert sender_events[0]["type"] == "message"
    assert sender_events[0]["is_read"] is True

    receipt = sender_events[1]
    assert receipt["type"] == "read_receipt"
    assert receipt["reader_id"] == receiver.id
    assert receipt["reader_display_name"] == receiver.display_name
    assert sender_events[0]["id"] in receipt["message_ids"]


async def test_ws_no_read_receipt_when_sender_is_only_connected_user(db_session: AsyncSession):
    """No read_receipt is broadcast if no other users are connected when message is sent."""
    user = await _create_user(db_session, "rdn-solo", "SoloUser")
    conv = await _create_conversation(db_session)
    await _add_member(db_session, conv.id, user.id)

    app.dependency_overrides[get_ws_user] = _override_ws_user(user)
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            with client.websocket_connect(f"/ws/chat/{conv.id}") as ws:
                ws.send_json({"content": "solo send"})
                data = ws.receive_json()
    finally:
        app.dependency_overrides.pop(get_ws_user, None)
        app.dependency_overrides.pop(get_db, None)

    # Only the message event is received — no read_receipt follows
    assert data["type"] == "message"
    assert data["content"] == "solo send"
