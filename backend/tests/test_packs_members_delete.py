"""Tests for DELETE /api/packs/{id}/members/{userId} endpoint."""

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
from app.models.pack_join_request_vote import PackJoinRequestVote, PackJoinRequestVoteDecision
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
    consensus_required: bool = False,
) -> Pack:
    pack = Pack(
        creator_id=creator_id,
        name=name,
        created_at=created_at,
        consensus_required=consensus_required,
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
) -> PackJoinRequest:
    join_request = PackJoinRequest(pack_id=pack_id, user_id=user_id, status=status)
    session.add(join_request)
    await session.commit()
    await session.refresh(join_request)
    return join_request


async def _add_vote(
    session: AsyncSession,
    *,
    join_request_id: int,
    voter_user_id: int,
    decision: PackJoinRequestVoteDecision,
) -> None:
    session.add(
        PackJoinRequestVote(
            join_request_id=join_request_id,
            voter_user_id=voter_user_id,
            decision=decision,
        )
    )
    await session.commit()


def test_delete_pack_member_requires_auth(client: TestClient):
    response = client.delete("/api/packs/1/members/2")

    assert response.status_code == 401


async def test_delete_pack_member_returns_404_when_pack_missing(pack_session: AsyncSession):
    current_user = await _create_user(pack_session, "pack-member-delete-missing", "Admin")

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(pack_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.delete("/api/packs/999/members/1")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 404
    assert response.json() == {"detail": "Pack not found"}


async def test_member_can_leave_pack(pack_session: AsyncSession):
    admin = await _create_user(pack_session, "pack-member-leave-admin", "Admin")
    member = await _create_user(pack_session, "pack-member-leave-member", "Member")
    pack = await _create_pack(
        pack_session,
        creator_id=admin.id,
        name="North Pack",
        created_at=datetime(2025, 1, 4),
    )
    await _add_member(pack_session, pack_id=pack.id, user_id=admin.id, role=PackMemberRole.ADMIN)
    await _add_member(pack_session, pack_id=pack.id, user_id=member.id)

    app.dependency_overrides[get_current_user] = _override_current_user(member)
    app.dependency_overrides[get_db] = _override_db(pack_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.delete(f"/api/packs/{pack.id}/members/{member.id}")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    remaining_members = (
        await pack_session.execute(select(PackMember).where(PackMember.pack_id == pack.id))
    ).scalars().all()

    assert response.status_code == 204
    assert response.content == b""
    assert [membership.user_id for membership in remaining_members] == [admin.id]


async def test_delete_pack_member_requires_admin_to_remove_others(pack_session: AsyncSession):
    admin = await _create_user(pack_session, "pack-member-delete-admin", "Admin")
    member = await _create_user(pack_session, "pack-member-delete-member", "Member")
    target = await _create_user(pack_session, "pack-member-delete-target", "Target")
    pack = await _create_pack(
        pack_session,
        creator_id=admin.id,
        name="North Pack",
        created_at=datetime(2025, 1, 4),
    )
    await _add_member(pack_session, pack_id=pack.id, user_id=admin.id, role=PackMemberRole.ADMIN)
    await _add_member(pack_session, pack_id=pack.id, user_id=member.id)
    await _add_member(pack_session, pack_id=pack.id, user_id=target.id)

    app.dependency_overrides[get_current_user] = _override_current_user(member)
    app.dependency_overrides[get_db] = _override_db(pack_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.delete(f"/api/packs/{pack.id}/members/{target.id}")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 403
    assert response.json() == {"detail": "Not authorized to remove this member"}


async def test_delete_pack_member_returns_404_when_member_missing(pack_session: AsyncSession):
    admin = await _create_user(pack_session, "pack-member-delete-missing-admin", "Admin")
    missing_user = await _create_user(
        pack_session,
        "pack-member-delete-missing-target",
        "Missing Target",
    )
    pack = await _create_pack(
        pack_session,
        creator_id=admin.id,
        name="North Pack",
        created_at=datetime(2025, 1, 4),
    )
    await _add_member(pack_session, pack_id=pack.id, user_id=admin.id, role=PackMemberRole.ADMIN)

    app.dependency_overrides[get_current_user] = _override_current_user(admin)
    app.dependency_overrides[get_db] = _override_db(pack_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.delete(f"/api/packs/{pack.id}/members/{missing_user.id}")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 404
    assert response.json() == {"detail": "Member not found"}


async def test_admin_can_remove_member_and_cleanup_pending_votes(pack_session: AsyncSession):
    admin = await _create_user(pack_session, "pack-member-remove-admin", "Admin")
    member = await _create_user(pack_session, "pack-member-remove-member", "Member")
    requester = await _create_user(pack_session, "pack-member-remove-requester", "Requester")
    pack = await _create_pack(
        pack_session,
        creator_id=admin.id,
        name="North Pack",
        created_at=datetime(2025, 1, 4),
        consensus_required=True,
    )
    await _add_member(pack_session, pack_id=pack.id, user_id=admin.id, role=PackMemberRole.ADMIN)
    await _add_member(pack_session, pack_id=pack.id, user_id=member.id)
    join_request = await _add_join_request(pack_session, pack_id=pack.id, user_id=requester.id)
    await _add_vote(
        pack_session,
        join_request_id=join_request.id,
        voter_user_id=member.id,
        decision=PackJoinRequestVoteDecision.APPROVED,
    )

    app.dependency_overrides[get_current_user] = _override_current_user(admin)
    app.dependency_overrides[get_db] = _override_db(pack_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.delete(f"/api/packs/{pack.id}/members/{member.id}")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    remaining_member = await pack_session.scalar(
        select(PackMember).where(
            PackMember.pack_id == pack.id,
            PackMember.user_id == member.id,
        )
    )
    remaining_vote = await pack_session.get(
        PackJoinRequestVote,
        {
            "join_request_id": join_request.id,
            "voter_user_id": member.id,
        },
    )

    assert response.status_code == 204
    assert remaining_member is None
    assert remaining_vote is None


async def test_delete_pack_member_rejects_removing_last_admin(pack_session: AsyncSession):
    admin = await _create_user(pack_session, "pack-member-last-admin", "Admin")
    pack = await _create_pack(
        pack_session,
        creator_id=admin.id,
        name="North Pack",
        created_at=datetime(2025, 1, 4),
    )
    await _add_member(pack_session, pack_id=pack.id, user_id=admin.id, role=PackMemberRole.ADMIN)

    app.dependency_overrides[get_current_user] = _override_current_user(admin)
    app.dependency_overrides[get_db] = _override_db(pack_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.delete(f"/api/packs/{pack.id}/members/{admin.id}")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    remaining_admin = await pack_session.scalar(
        select(PackMember).where(
            PackMember.pack_id == pack.id,
            PackMember.user_id == admin.id,
        )
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Cannot remove the last admin"}
    assert remaining_admin is not None
