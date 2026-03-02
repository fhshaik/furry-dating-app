from collections.abc import Iterable
from typing import Protocol

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.match import Match
from app.models.message import Message
from app.models.notification import Notification
from app.models.pack_join_request import PackJoinRequest


class MatchNotifier(Protocol):
    async def notify_match_created(self, match: Match) -> None: ...


class PackJoinRequestNotifier(Protocol):
    async def notify_pack_join_request_received(
        self,
        join_request: PackJoinRequest,
        recipient_user_ids: Iterable[int],
    ) -> None: ...


class MessageNotifier(Protocol):
    async def notify_message_received(
        self,
        message: Message,
        recipient_user_ids: Iterable[int],
    ) -> None: ...


class DatabaseNotificationService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def notify_match_created(self, match: Match) -> None:
        self._db.add_all(
            [
                Notification(
                    user_id=user_id,
                    type="match_created",
                    payload={
                        "match_id": match.id,
                        "user_a_id": match.user_a_id,
                        "user_b_id": match.user_b_id,
                    },
                )
                for user_id in (match.user_a_id, match.user_b_id)
            ]
        )
        await self._db.commit()

    async def notify_pack_join_request_received(
        self,
        join_request: PackJoinRequest,
        recipient_user_ids: Iterable[int],
    ) -> None:
        recipient_ids = list(dict.fromkeys(recipient_user_ids))
        if not recipient_ids:
            return

        self._db.add_all(
            [
                Notification(
                    user_id=user_id,
                    type="pack_join_request_received",
                    payload={
                        "pack_id": join_request.pack_id,
                        "join_request_id": join_request.id,
                        "requester_user_id": join_request.user_id,
                    },
                )
                for user_id in recipient_ids
            ]
        )
        await self._db.commit()

    async def notify_message_received(
        self,
        message: Message,
        recipient_user_ids: Iterable[int],
    ) -> None:
        recipient_ids = list(dict.fromkeys(recipient_user_ids))
        if not recipient_ids:
            return

        self._db.add_all(
            [
                Notification(
                    user_id=user_id,
                    type="message_received",
                    payload={
                        "conversation_id": message.conversation_id,
                        "message_id": message.id,
                        "sender_id": message.sender_id,
                    },
                )
                for user_id in recipient_ids
            ]
        )
        await self._db.commit()


def build_notification_service(db: AsyncSession) -> DatabaseNotificationService:
    return DatabaseNotificationService(db)


def get_match_notifier(
    db: AsyncSession = Depends(get_db),
) -> MatchNotifier:
    return build_notification_service(db)


def get_pack_join_request_notifier(
    db: AsyncSession = Depends(get_db),
) -> PackJoinRequestNotifier:
    return build_notification_service(db)


def get_message_notifier(
    db: AsyncSession = Depends(get_db),
) -> MessageNotifier:
    return build_notification_service(db)
