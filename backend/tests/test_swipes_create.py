"""Tests for POST /api/swipes endpoint."""

from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.deps import get_current_user
from app.database import Base, get_db
from app.main import app
from app.models.conversation import Conversation
from app.models.conversation_member import ConversationMember
from app.models.match import Match
from app.models.notification import Notification
from app.models.pack import Pack
from app.models.swipe import Swipe, SwipeAction
from app.models.user import User
from app.services.notifications import get_match_notifier


@pytest.fixture()
async def swipe_session():
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


def _override_match_notifier(notifier: AsyncMock):
    def _override():
        return notifier

    return _override


async def _create_user(session: AsyncSession, oauth_id: str, display_name: str) -> User:
    user = User(
        oauth_provider="google",
        oauth_id=oauth_id,
        email=f"{oauth_id}@example.com",
        display_name=display_name,
        created_at=datetime(2025, 1, 1),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def _create_pack(session: AsyncSession, creator_id: int, name: str) -> Pack:
    pack = Pack(creator_id=creator_id, name=name)
    session.add(pack)
    await session.commit()
    await session.refresh(pack)
    return pack


def test_create_swipe_requires_auth(client: TestClient):
    response = client.post("/api/swipes", json={"action": "like", "target_user_id": 2})

    assert response.status_code == 401


async def test_create_swipe_records_user_pass(swipe_session: AsyncSession):
    current_user = await _create_user(swipe_session, "swiper-pass", "Swiper")
    target_user = await _create_user(swipe_session, "target-pass", "Target")
    notifier = AsyncMock()

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(swipe_session)
    app.dependency_overrides[get_match_notifier] = _override_match_notifier(notifier)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.post(
                "/api/swipes",
                json={"action": "pass", "target_user_id": target_user.id},
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_match_notifier, None)

    assert response.status_code == 201
    data = response.json()
    assert data["swiper_id"] == current_user.id
    assert data["target_user_id"] == target_user.id
    assert data["target_pack_id"] is None
    assert data["action"] == "pass"
    assert data["is_match"] is False

    swipes = (await swipe_session.execute(select(Swipe))).scalars().all()
    assert len(swipes) == 1
    assert swipes[0].action == SwipeAction.PASS
    notifier.notify_match_created.assert_not_called()


async def test_create_swipe_creates_match_for_mutual_like(swipe_session: AsyncSession):
    current_user = await _create_user(swipe_session, "mutual-current", "Current")
    target_user = await _create_user(swipe_session, "mutual-target", "Target")
    notifier = AsyncMock()

    swipe_session.add(
        Swipe(
            swiper_id=target_user.id,
            target_user_id=current_user.id,
            action=SwipeAction.LIKE,
        )
    )
    await swipe_session.commit()

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(swipe_session)
    app.dependency_overrides[get_match_notifier] = _override_match_notifier(notifier)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.post(
                "/api/swipes",
                json={"action": "like", "target_user_id": target_user.id},
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_match_notifier, None)

    assert response.status_code == 201
    assert response.json()["is_match"] is True

    matches = (await swipe_session.execute(select(Match))).scalars().all()
    assert len(matches) == 1
    assert {matches[0].user_a_id, matches[0].user_b_id} == {current_user.id, target_user.id}
    notifier.notify_match_created.assert_awaited_once()
    notified_match = notifier.notify_match_created.await_args.args[0]
    assert notified_match.id == matches[0].id
    assert {notified_match.user_a_id, notified_match.user_b_id} == {
        current_user.id,
        target_user.id,
    }


async def test_create_swipe_persists_match_notifications(swipe_session: AsyncSession):
    current_user = await _create_user(swipe_session, "mutual-notify-current", "Current")
    target_user = await _create_user(swipe_session, "mutual-notify-target", "Target")

    swipe_session.add(
        Swipe(
            swiper_id=target_user.id,
            target_user_id=current_user.id,
            action=SwipeAction.LIKE,
        )
    )
    await swipe_session.commit()

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(swipe_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.post(
                "/api/swipes",
                json={"action": "like", "target_user_id": target_user.id},
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 201
    notifications = (
        await swipe_session.execute(select(Notification).order_by(Notification.user_id.asc()))
    ).scalars().all()

    assert len(notifications) == 2
    assert [notification.user_id for notification in notifications] == [current_user.id, target_user.id]
    assert {notification.type for notification in notifications} == {"match_created"}
    assert all(notification.payload["match_id"] is not None for notification in notifications)


async def test_create_swipe_does_not_duplicate_existing_active_match(swipe_session: AsyncSession):
    current_user = await _create_user(swipe_session, "duplicate-current", "Current")
    target_user = await _create_user(swipe_session, "duplicate-target", "Target")
    notifier = AsyncMock()

    swipe_session.add(
        Match(
            user_a_id=current_user.id,
            user_b_id=target_user.id,
        )
    )
    swipe_session.add(
        Swipe(
            swiper_id=target_user.id,
            target_user_id=current_user.id,
            action=SwipeAction.LIKE,
        )
    )
    await swipe_session.commit()

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(swipe_session)
    app.dependency_overrides[get_match_notifier] = _override_match_notifier(notifier)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.post(
                "/api/swipes",
                json={"action": "like", "target_user_id": target_user.id},
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_match_notifier, None)

    assert response.status_code == 201
    assert response.json()["is_match"] is False

    matches = (await swipe_session.execute(select(Match))).scalars().all()
    assert len(matches) == 1
    notifier.notify_match_created.assert_not_called()


async def test_create_swipe_records_pack_target(swipe_session: AsyncSession):
    current_user = await _create_user(swipe_session, "pack-current", "Current")
    pack_creator = await _create_user(swipe_session, "pack-creator", "Creator")
    pack = await _create_pack(swipe_session, creator_id=pack_creator.id, name="Moon Pack")

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(swipe_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.post(
                "/api/swipes",
                json={"action": "like", "target_pack_id": pack.id},
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 201
    data = response.json()
    assert data["target_pack_id"] == pack.id
    assert data["target_user_id"] is None
    assert data["is_match"] is False


async def test_create_swipe_rejects_swiping_on_self(swipe_session: AsyncSession):
    current_user = await _create_user(swipe_session, "self-current", "Current")

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(swipe_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.post(
                "/api/swipes",
                json={"action": "like", "target_user_id": current_user.id},
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 400
    assert response.json()["detail"] == "Cannot swipe on yourself"


async def test_create_swipe_rejects_missing_target(swipe_session: AsyncSession):
    current_user = await _create_user(swipe_session, "missing-target", "Current")

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(swipe_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.post("/api/swipes", json={"action": "like"})
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 422
    assert "Exactly one of target_user_id or target_pack_id must be provided" in str(
        response.json()["detail"]
    )


async def test_create_swipe_rejects_multiple_targets(swipe_session: AsyncSession):
    current_user = await _create_user(swipe_session, "multiple-targets", "Current")
    target_user = await _create_user(swipe_session, "multiple-targets-user", "Target")
    pack = await _create_pack(swipe_session, creator_id=current_user.id, name="Dual Pack")

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(swipe_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.post(
                "/api/swipes",
                json={
                    "action": "like",
                    "target_user_id": target_user.id,
                    "target_pack_id": pack.id,
                },
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 422
    assert "Exactly one of target_user_id or target_pack_id must be provided" in str(
        response.json()["detail"]
    )


async def test_create_swipe_rejects_unknown_user_target(swipe_session: AsyncSession):
    current_user = await _create_user(swipe_session, "missing-user", "Current")

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(swipe_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.post(
                "/api/swipes",
                json={"action": "like", "target_user_id": 999},
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 404
    assert response.json()["detail"] == "Target user not found"


async def test_create_swipe_creates_direct_conversation_on_mutual_like(
    swipe_session: AsyncSession,
):
    current_user = await _create_user(swipe_session, "conv-current", "Current")
    target_user = await _create_user(swipe_session, "conv-target", "Target")
    notifier = AsyncMock()

    swipe_session.add(
        Swipe(
            swiper_id=target_user.id,
            target_user_id=current_user.id,
            action=SwipeAction.LIKE,
        )
    )
    await swipe_session.commit()

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(swipe_session)
    app.dependency_overrides[get_match_notifier] = _override_match_notifier(notifier)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.post(
                "/api/swipes",
                json={"action": "like", "target_user_id": target_user.id},
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_match_notifier, None)

    assert response.status_code == 201
    assert response.json()["is_match"] is True

    conversations = (await swipe_session.execute(select(Conversation))).scalars().all()
    assert len(conversations) == 1
    assert conversations[0].type.value == "direct"
    assert conversations[0].pack_id is None

    members = (
        (await swipe_session.execute(select(ConversationMember))).scalars().all()
    )
    member_user_ids = {m.user_id for m in members}
    assert member_user_ids == {current_user.id, target_user.id}


async def test_create_swipe_does_not_create_conversation_without_match(
    swipe_session: AsyncSession,
):
    current_user = await _create_user(swipe_session, "no-conv-current", "Current")
    target_user = await _create_user(swipe_session, "no-conv-target", "Target")
    notifier = AsyncMock()

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(swipe_session)
    app.dependency_overrides[get_match_notifier] = _override_match_notifier(notifier)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.post(
                "/api/swipes",
                json={"action": "like", "target_user_id": target_user.id},
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_match_notifier, None)

    assert response.status_code == 201
    assert response.json()["is_match"] is False

    conversations = (await swipe_session.execute(select(Conversation))).scalars().all()
    assert len(conversations) == 0
