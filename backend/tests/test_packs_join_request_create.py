"""Tests for POST /api/packs/{id}/join-request endpoint."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.deps import get_current_user
from app.database import Base, get_db
from app.main import app
from app.models.notification import Notification
from app.models.pack import Pack
from app.models.pack_join_request import PackJoinRequest, PackJoinRequestStatus
from app.models.pack_member import PackMember, PackMemberRole
from app.models.user import User


@pytest.fixture()
async def pack_session():
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
        created_at=datetime(2025, 1, 1),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def _create_pack(
    session: AsyncSession,
    *,
    creator_id: int,
    name: str,
    is_open: bool = True,
    created_at: datetime,
) -> Pack:
    pack = Pack(
        creator_id=creator_id,
        name=name,
        is_open=is_open,
        created_at=created_at,
    )
    session.add(pack)
    await session.commit()
    await session.refresh(pack)
    return pack


async def _add_member(
    session: AsyncSession,
    *,
    pack_id: int,
    user_id: int,
    role: PackMemberRole = PackMemberRole.MEMBER,
) -> None:
    session.add(PackMember(pack_id=pack_id, user_id=user_id, role=role))
    await session.commit()


async def _add_join_request(
    session: AsyncSession,
    *,
    pack_id: int,
    user_id: int,
    status: PackJoinRequestStatus = PackJoinRequestStatus.PENDING,
) -> None:
    session.add(PackJoinRequest(pack_id=pack_id, user_id=user_id, status=status))
    await session.commit()


def test_create_pack_join_request_requires_auth(client: TestClient):
    response = client.post("/api/packs/1/join-request")

    assert response.status_code == 401


async def test_create_pack_join_request_returns_404_when_pack_missing(pack_session: AsyncSession):
    current_user = await _create_user(pack_session, "join-request-missing", "Requester")

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(pack_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.post("/api/packs/999/join-request")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 404
    assert response.json() == {"detail": "Pack not found"}


async def test_create_pack_join_request_rejects_closed_pack(pack_session: AsyncSession):
    creator = await _create_user(pack_session, "join-request-closed-owner", "Owner")
    current_user = await _create_user(pack_session, "join-request-closed-user", "Requester")
    pack = await _create_pack(
        pack_session,
        creator_id=creator.id,
        name="Private Pack",
        is_open=False,
        created_at=datetime(2025, 1, 3),
    )

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(pack_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.post(f"/api/packs/{pack.id}/join-request")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 403
    assert response.json() == {"detail": "Pack is not open to join requests"}


async def test_create_pack_join_request_rejects_existing_member(pack_session: AsyncSession):
    creator = await _create_user(pack_session, "join-request-member-owner", "Owner")
    current_user = await _create_user(pack_session, "join-request-member-user", "Member")
    pack = await _create_pack(
        pack_session,
        creator_id=creator.id,
        name="North Pack",
        created_at=datetime(2025, 1, 3),
    )
    await _add_member(pack_session, pack_id=pack.id, user_id=current_user.id)

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(pack_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.post(f"/api/packs/{pack.id}/join-request")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 400
    assert response.json() == {"detail": "Already a member of this pack"}


async def test_create_pack_join_request_rejects_duplicate_pending_request(
    pack_session: AsyncSession,
):
    creator = await _create_user(pack_session, "join-request-duplicate-owner", "Owner")
    current_user = await _create_user(pack_session, "join-request-duplicate-user", "Requester")
    pack = await _create_pack(
        pack_session,
        creator_id=creator.id,
        name="North Pack",
        created_at=datetime(2025, 1, 3),
    )
    await _add_join_request(pack_session, pack_id=pack.id, user_id=current_user.id)

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(pack_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.post(f"/api/packs/{pack.id}/join-request")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 409
    assert response.json() == {"detail": "Join request already pending"}


async def test_create_pack_join_request_creates_pending_request(pack_session: AsyncSession):
    creator = await _create_user(pack_session, "join-request-create-owner", "Owner")
    current_user = await _create_user(pack_session, "join-request-create-user", "Requester")
    pack = await _create_pack(
        pack_session,
        creator_id=creator.id,
        name="North Pack",
        created_at=datetime(2025, 1, 3),
    )

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(pack_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.post(f"/api/packs/{pack.id}/join-request")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 201
    data = response.json()
    assert data["pack_id"] == pack.id
    assert data["user_id"] == current_user.id
    assert data["status"] == "pending"
    assert data["id"] is not None
    assert data["created_at"] is not None

    join_requests = (
        await pack_session.execute(select(PackJoinRequest).where(PackJoinRequest.pack_id == pack.id))
    ).scalars().all()
    assert len(join_requests) == 1
    assert join_requests[0].user_id == current_user.id
    assert join_requests[0].status == PackJoinRequestStatus.PENDING


async def test_create_pack_join_request_notifies_pack_admins(pack_session: AsyncSession):
    creator = await _create_user(pack_session, "join-request-notify-owner", "Owner")
    admin = await _create_user(pack_session, "join-request-notify-admin", "Admin")
    current_user = await _create_user(pack_session, "join-request-notify-user", "Requester")
    pack = await _create_pack(
        pack_session,
        creator_id=creator.id,
        name="North Pack",
        created_at=datetime(2025, 1, 3),
    )
    await _add_member(pack_session, pack_id=pack.id, user_id=creator.id, role=PackMemberRole.ADMIN)
    await _add_member(pack_session, pack_id=pack.id, user_id=admin.id, role=PackMemberRole.ADMIN)

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(pack_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.post(f"/api/packs/{pack.id}/join-request")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 201
    notifications = (
        await pack_session.execute(select(Notification).order_by(Notification.user_id.asc()))
    ).scalars().all()

    assert [notification.user_id for notification in notifications] == [creator.id, admin.id]
    assert {notification.type for notification in notifications} == {"pack_join_request_received"}
    assert all(notification.payload["pack_id"] == pack.id for notification in notifications)
    assert all(notification.payload["requester_user_id"] == current_user.id for notification in notifications)


async def test_create_pack_join_request_notifies_all_members_when_consensus_required(
    pack_session: AsyncSession,
):
    creator = await _create_user(pack_session, "join-request-consensus-owner", "Owner")
    member = await _create_user(pack_session, "join-request-consensus-member", "Member")
    current_user = await _create_user(pack_session, "join-request-consensus-user", "Requester")
    pack = await _create_pack(
        pack_session,
        creator_id=creator.id,
        name="Consensus Pack",
        created_at=datetime(2025, 1, 3),
    )
    pack.consensus_required = True
    await pack_session.commit()
    await _add_member(pack_session, pack_id=pack.id, user_id=creator.id, role=PackMemberRole.ADMIN)
    await _add_member(pack_session, pack_id=pack.id, user_id=member.id, role=PackMemberRole.MEMBER)

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(pack_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.post(f"/api/packs/{pack.id}/join-request")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 201
    notifications = (
        await pack_session.execute(select(Notification).order_by(Notification.user_id.asc()))
    ).scalars().all()

    assert [notification.user_id for notification in notifications] == [creator.id, member.id]
    assert {notification.type for notification in notifications} == {"pack_join_request_received"}
