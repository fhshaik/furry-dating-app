import logging

from authlib.jose.errors import JoseError
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.database import get_db
from app.models.conversation import Conversation
from app.models.conversation_member import ConversationMember
from app.models.message import Message
from app.models.user import User
from app.schemas.conversation import ChatMessageCreate
from app.services.notifications import build_notification_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ws"])

_COOKIE_NAME = "access_token"


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[int, list[WebSocket]] = {}
        # conv_id -> user_id -> list of WebSockets (a user may open multiple tabs)
        self._user_connections: dict[int, dict[int, list[WebSocket]]] = {}

    async def connect(self, conversation_id: int, user_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.setdefault(conversation_id, []).append(websocket)
        self._user_connections.setdefault(conversation_id, {}).setdefault(user_id, []).append(
            websocket
        )

    def disconnect(self, conversation_id: int, user_id: int, websocket: WebSocket) -> None:
        bucket = self._connections.get(conversation_id)
        if bucket:
            bucket[:] = [ws for ws in bucket if ws is not websocket]
            if not bucket:
                del self._connections[conversation_id]

        user_bucket = self._user_connections.get(conversation_id, {}).get(user_id, [])
        user_bucket[:] = [ws for ws in user_bucket if ws is not websocket]
        if not user_bucket:
            self._user_connections.get(conversation_id, {}).pop(user_id, None)
        if not self._user_connections.get(conversation_id):
            self._user_connections.pop(conversation_id, None)

    def has_other_connected_users(self, conversation_id: int, sender_id: int) -> bool:
        """Return True if any user other than sender_id is currently connected."""
        users = self._user_connections.get(conversation_id, {})
        return any(uid != sender_id for uid in users)

    def get_connected_other_user_ids(self, conversation_id: int, sender_id: int) -> list[int]:
        """Return user IDs of users connected to this conversation other than sender_id."""
        users = self._user_connections.get(conversation_id, {})
        return [uid for uid in users if uid != sender_id]

    async def broadcast(self, conversation_id: int, payload: dict) -> None:
        for websocket in list(self._connections.get(conversation_id, [])):
            try:
                await websocket.send_json(payload)
            except Exception:
                logger.debug("Failed to send to websocket; skipping", exc_info=True)


manager = ConnectionManager()


_QUERY_PARAM_NAME = "token"


async def get_ws_user(
    websocket: WebSocket,
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Authenticate WebSocket connection via httpOnly JWT cookie or ?token= query param."""
    token = websocket.cookies.get(_COOKIE_NAME) or websocket.query_params.get(
        _QUERY_PARAM_NAME
    )
    if not token:
        return None
    try:
        claims = decode_access_token(token)
        user_id = int(claims["sub"])
    except (JoseError, KeyError, ValueError):
        return None
    return await db.get(User, user_id)


@router.websocket("/ws/chat/{conversation_id}")
async def websocket_chat(
    conversation_id: int,
    websocket: WebSocket,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_ws_user),
) -> None:
    if user is None:
        await websocket.close(code=4001)
        return

    conversation = await db.get(Conversation, conversation_id)
    if conversation is None:
        await websocket.close(code=4004)
        return

    member = await db.scalar(
        select(ConversationMember).where(
            ConversationMember.conversation_id == conversation_id,
            ConversationMember.user_id == user.id,
        )
    )
    if member is None:
        await websocket.close(code=4003)
        return

    notification_service = build_notification_service(db)

    await manager.connect(conversation_id, user.id, websocket)
    try:
        # Mark all unread messages (sent by others) as read on connect.
        unread_msgs = (
            await db.scalars(
                select(Message).where(
                    Message.conversation_id == conversation_id,
                    Message.sender_id != user.id,
                    Message.is_read == False,  # noqa: E712
                )
            )
        ).all()
        if unread_msgs:
            for m in unread_msgs:
                m.is_read = True
            await db.commit()
            await manager.broadcast(
                conversation_id,
                {
                    "type": "read_receipt",
                    "message_ids": [m.id for m in unread_msgs],
                    "reader_id": user.id,
                    "reader_display_name": user.display_name,
                },
            )

        while True:
            data = await websocket.receive_json()
            try:
                payload = ChatMessageCreate.model_validate(data)
            except ValidationError:
                continue

            msg = Message(
                conversation_id=conversation_id,
                sender_id=user.id,
                content=payload.content,
            )
            db.add(msg)
            await db.commit()
            await db.refresh(msg)

            # If any recipient is already connected, mark the message as read immediately.
            reader_ids: list[int] = []
            if manager.has_other_connected_users(conversation_id, user.id):
                msg.is_read = True
                await db.commit()
                reader_ids = manager.get_connected_other_user_ids(conversation_id, user.id)

            recipient_query = select(ConversationMember.user_id).where(
                ConversationMember.conversation_id == conversation_id,
                ConversationMember.user_id != user.id,
            )
            if reader_ids:
                recipient_query = recipient_query.where(ConversationMember.user_id.not_in(reader_ids))

            recipient_ids = (await db.scalars(recipient_query)).all()
            await notification_service.notify_message_received(msg, recipient_ids)

            await manager.broadcast(
                conversation_id,
                {
                    "type": "message",
                    "id": msg.id,
                    "conversation_id": msg.conversation_id,
                    "sender_id": msg.sender_id,
                    "content": msg.content,
                    "sent_at": msg.sent_at.isoformat(),
                    "is_read": msg.is_read,
                },
            )

            # Broadcast a read_receipt for each recipient who was already connected.
            if reader_ids:
                readers = (
                    await db.scalars(select(User).where(User.id.in_(reader_ids)))
                ).all()
                for reader in readers:
                    await manager.broadcast(
                        conversation_id,
                        {
                            "type": "read_receipt",
                            "message_ids": [msg.id],
                            "reader_id": reader.id,
                            "reader_display_name": reader.display_name,
                        },
                    )
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(conversation_id, user.id, websocket)
