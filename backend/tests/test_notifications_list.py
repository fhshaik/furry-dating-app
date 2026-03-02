"""Tests for GET /api/notifications endpoint."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.deps import get_current_user
from app.database import Base, get_db
from app.main import app
from app.models.notification import Notification
from app.models.user import User


@pytest.fixture()
async def notifications_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture()
def client():
    with TestClient(app, follow_redirects=False) as c:
        yield c


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


def test_list_notifications_requires_auth(client: TestClient):
    response = client.get("/api/notifications")

    assert response.status_code == 401


async def test_list_notifications_returns_unread_first_and_only_current_user_items(
    notifications_session: AsyncSession,
):
    current_user = await _create_user(notifications_session, "notif-current", "Current")
    other_user = await _create_user(notifications_session, "notif-other", "Other")

    notifications_session.add_all(
        [
            Notification(
                user_id=current_user.id,
                type="message_received",
                payload={"message_id": 1},
                is_read=True,
                created_at=datetime(2025, 2, 1, 12, 0, 0),
            ),
            Notification(
                user_id=current_user.id,
                type="match_created",
                payload={"match_id": 7},
                is_read=False,
                created_at=datetime(2025, 2, 3, 12, 0, 0),
            ),
            Notification(
                user_id=current_user.id,
                type="pack_join_request_received",
                payload={"join_request_id": 9},
                is_read=False,
                created_at=datetime(2025, 2, 2, 12, 0, 0),
            ),
            Notification(
                user_id=other_user.id,
                type="message_received",
                payload={"message_id": 99},
                is_read=False,
                created_at=datetime(2025, 2, 4, 12, 0, 0),
            ),
        ]
    )
    await notifications_session.commit()

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(notifications_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.get("/api/notifications")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["limit"] == 20
    assert data["total"] == 3
    assert data["has_more"] is False
    assert [item["type"] for item in data["items"]] == [
        "match_created",
        "pack_join_request_received",
        "message_received",
    ]
    assert [item["is_read"] for item in data["items"]] == [False, False, True]
    assert all(item["payload"] is not None for item in data["items"])


async def test_list_notifications_paginates_sorted_results(
    notifications_session: AsyncSession,
):
    current_user = await _create_user(notifications_session, "notif-page-current", "Current")

    notifications_session.add_all(
        [
            Notification(
                user_id=current_user.id,
                type="first-unread",
                payload={"order": 1},
                is_read=False,
                created_at=datetime(2025, 2, 4, 10, 0, 0),
            ),
            Notification(
                user_id=current_user.id,
                type="second-unread",
                payload={"order": 2},
                is_read=False,
                created_at=datetime(2025, 2, 3, 10, 0, 0),
            ),
            Notification(
                user_id=current_user.id,
                type="first-read",
                payload={"order": 3},
                is_read=True,
                created_at=datetime(2025, 2, 5, 10, 0, 0),
            ),
        ]
    )
    await notifications_session.commit()

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(notifications_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.get("/api/notifications?page=2&limit=1")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 2
    assert data["limit"] == 1
    assert data["total"] == 3
    assert data["has_more"] is True
    assert [item["type"] for item in data["items"]] == ["second-unread"]


def test_mark_notification_read_requires_auth(client: TestClient):
    response = client.patch("/api/notifications/1/read")

    assert response.status_code == 401


def test_mark_all_notifications_read_requires_auth(client: TestClient):
    response = client.patch("/api/notifications/read-all")

    assert response.status_code == 401


async def test_mark_notification_read_marks_current_user_notification_as_read(
    notifications_session: AsyncSession,
):
    current_user = await _create_user(notifications_session, "notif-read-current", "Current")
    notification = Notification(
        user_id=current_user.id,
        type="message_received",
        payload={"message_id": 1},
        is_read=False,
        created_at=datetime(2025, 2, 6, 12, 0, 0),
    )
    notifications_session.add(notification)
    await notifications_session.commit()
    await notifications_session.refresh(notification)

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(notifications_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.patch(f"/api/notifications/{notification.id}/read")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == notification.id
    assert data["is_read"] is True

    await notifications_session.refresh(notification)
    assert notification.is_read is True


async def test_mark_notification_read_returns_404_for_other_users_notification(
    notifications_session: AsyncSession,
):
    current_user = await _create_user(notifications_session, "notif-read-owner", "Owner")
    other_user = await _create_user(notifications_session, "notif-read-other", "Other")
    notification = Notification(
        user_id=other_user.id,
        type="match_created",
        payload={"match_id": 9},
        is_read=False,
        created_at=datetime(2025, 2, 7, 12, 0, 0),
    )
    notifications_session.add(notification)
    await notifications_session.commit()
    await notifications_session.refresh(notification)

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(notifications_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.patch(f"/api/notifications/{notification.id}/read")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 404
    assert response.json() == {"detail": "Notification not found"}


async def test_mark_all_notifications_read_marks_only_current_user_notifications(
    notifications_session: AsyncSession,
):
    current_user = await _create_user(notifications_session, "notif-read-all-current", "Current")
    other_user = await _create_user(notifications_session, "notif-read-all-other", "Other")

    notifications_session.add_all(
        [
            Notification(
                user_id=current_user.id,
                type="message_received",
                payload={"message_id": 1},
                is_read=False,
                created_at=datetime(2025, 2, 8, 12, 0, 0),
            ),
            Notification(
                user_id=current_user.id,
                type="match_created",
                payload={"match_id": 2},
                is_read=True,
                created_at=datetime(2025, 2, 8, 13, 0, 0),
            ),
            Notification(
                user_id=current_user.id,
                type="pack_join_request_received",
                payload={"join_request_id": 3},
                is_read=False,
                created_at=datetime(2025, 2, 8, 14, 0, 0),
            ),
            Notification(
                user_id=other_user.id,
                type="message_received",
                payload={"message_id": 99},
                is_read=False,
                created_at=datetime(2025, 2, 8, 15, 0, 0),
            ),
        ]
    )
    await notifications_session.commit()

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(notifications_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.patch("/api/notifications/read-all")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 204
    assert response.content == b""

    current_user_notifications = list(
        (
            await notifications_session.execute(
                select(Notification)
                .where(Notification.user_id == current_user.id)
                .order_by(Notification.id.asc())
            )
        )
        .scalars()
        .all()
    )
    other_user_notification = await notifications_session.scalar(
        select(Notification).where(Notification.user_id == other_user.id)
    )

    assert [item.is_read for item in current_user_notifications] == [True, True, True]
    assert other_user_notification is not None
    assert other_user_notification.is_read is False
