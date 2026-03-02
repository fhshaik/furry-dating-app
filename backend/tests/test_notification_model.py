"""Tests for the Notification ORM model."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.notification import Notification
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


def test_notification_tablename():
    assert Notification.__tablename__ == "notifications"


def test_notification_has_required_columns():
    column_names = set(Notification.__table__.c.keys())
    assert "id" in column_names
    assert "user_id" in column_names
    assert "type" in column_names
    assert "payload" in column_names
    assert "is_read" in column_names
    assert "created_at" in column_names


async def test_create_notification(sqlite_session: AsyncSession):
    user = User(oauth_provider="google", oauth_id="notif-user-1", display_name="Fox")
    sqlite_session.add(user)
    await sqlite_session.commit()

    notification = Notification(
        user_id=user.id,
        type="match_created",
        payload={"match_id": 42, "message": "New match"},
    )
    sqlite_session.add(notification)
    await sqlite_session.commit()
    await sqlite_session.refresh(notification)

    assert notification.id is not None
    assert notification.user_id == user.id
    assert notification.type == "match_created"
    assert notification.payload == {"match_id": 42, "message": "New match"}
    assert notification.is_read is False
    assert notification.created_at is not None


async def test_notification_is_read_can_be_set_true(sqlite_session: AsyncSession):
    user = User(oauth_provider="google", oauth_id="notif-user-2", display_name="Wolf")
    sqlite_session.add(user)
    await sqlite_session.commit()

    notification = Notification(
        user_id=user.id,
        type="message_received",
        payload={"conversation_id": 7},
        is_read=True,
    )
    sqlite_session.add(notification)
    await sqlite_session.commit()
    await sqlite_session.refresh(notification)

    assert notification.is_read is True
