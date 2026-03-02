"""Tests for DELETE /api/packs/{id} endpoint."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.deps import get_current_user
from app.database import Base, get_db
from app.main import app
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
    created_at: datetime,
) -> Pack:
    pack = Pack(
        creator_id=creator_id,
        name=name,
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


def test_delete_pack_requires_auth(client: TestClient):
    response = client.delete("/api/packs/1")

    assert response.status_code == 401


async def test_delete_pack_returns_404_when_missing(pack_session: AsyncSession):
    current_user = await _create_user(pack_session, "pack-delete-missing", "Admin")

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(pack_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.delete("/api/packs/999")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 404
    assert response.json() == {"detail": "Pack not found"}


async def test_delete_pack_requires_admin_membership(pack_session: AsyncSession):
    creator = await _create_user(pack_session, "pack-delete-creator", "Creator")
    current_user = await _create_user(pack_session, "pack-delete-member", "Member")
    pack = await _create_pack(
        pack_session,
        creator_id=creator.id,
        name="North Pack",
        created_at=datetime(2025, 1, 3),
    )
    await _add_member(pack_session, pack_id=pack.id, user_id=creator.id, role=PackMemberRole.ADMIN)
    await _add_member(pack_session, pack_id=pack.id, user_id=current_user.id)

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(pack_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.delete(f"/api/packs/{pack.id}")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 403
    assert response.json() == {"detail": "Not authorized to delete this pack"}


async def test_delete_pack_removes_pack_members_and_join_requests(pack_session: AsyncSession):
    admin = await _create_user(pack_session, "pack-delete-admin", "Admin")
    member = await _create_user(pack_session, "pack-delete-member-2", "Member")
    requester = await _create_user(pack_session, "pack-delete-requester", "Requester")
    other_owner = await _create_user(pack_session, "pack-delete-other-owner", "Other Owner")

    pack = await _create_pack(
        pack_session,
        creator_id=admin.id,
        name="North Pack",
        created_at=datetime(2025, 1, 3),
    )
    other_pack = await _create_pack(
        pack_session,
        creator_id=other_owner.id,
        name="South Pack",
        created_at=datetime(2025, 1, 4),
    )

    await _add_member(pack_session, pack_id=pack.id, user_id=admin.id, role=PackMemberRole.ADMIN)
    await _add_member(pack_session, pack_id=pack.id, user_id=member.id)
    await _add_member(
        pack_session,
        pack_id=other_pack.id,
        user_id=other_owner.id,
        role=PackMemberRole.ADMIN,
    )
    await _add_join_request(pack_session, pack_id=pack.id, user_id=requester.id)

    app.dependency_overrides[get_current_user] = _override_current_user(admin)
    app.dependency_overrides[get_db] = _override_db(pack_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.delete(f"/api/packs/{pack.id}")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    deleted_pack = await pack_session.get(Pack, pack.id)
    remaining_members = (
        await pack_session.execute(select(PackMember).where(PackMember.pack_id == pack.id))
    ).scalars().all()
    remaining_requests = (
        await pack_session.execute(
            select(PackJoinRequest).where(PackJoinRequest.pack_id == pack.id)
        )
    ).scalars().all()
    preserved_pack = await pack_session.get(Pack, other_pack.id)

    assert response.status_code == 204
    assert response.content == b""
    assert deleted_pack is None
    assert remaining_members == []
    assert remaining_requests == []
    assert preserved_pack is not None
