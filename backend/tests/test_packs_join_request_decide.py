"""Tests for PATCH /api/packs/{id}/join-requests/{userId} endpoint."""

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
    max_size: int = 10,
) -> Pack:
    pack = Pack(
        creator_id=creator_id,
        name=name,
        created_at=created_at,
        consensus_required=consensus_required,
        max_size=max_size,
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


def test_decide_pack_join_request_requires_auth(client: TestClient):
    response = client.patch("/api/packs/1/join-requests/2", json={"status": "approved"})

    assert response.status_code == 401


async def test_decide_pack_join_request_returns_404_when_pack_missing(pack_session: AsyncSession):
    current_user = await _create_user(pack_session, "join-request-decide-missing", "Admin")

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(pack_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.patch("/api/packs/999/join-requests/1", json={"status": "approved"})
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 404
    assert response.json() == {"detail": "Pack not found"}


async def test_decide_pack_join_request_requires_admin_membership(pack_session: AsyncSession):
    owner = await _create_user(pack_session, "join-request-decide-owner", "Owner")
    member = await _create_user(pack_session, "join-request-decide-member", "Member")
    requester = await _create_user(pack_session, "join-request-decide-requester", "Requester")
    pack = await _create_pack(
        pack_session,
        creator_id=owner.id,
        name="North Pack",
        created_at=datetime(2025, 1, 2),
    )
    await _add_member(pack_session, pack_id=pack.id, user_id=owner.id, role=PackMemberRole.ADMIN)
    await _add_member(pack_session, pack_id=pack.id, user_id=member.id)
    await _add_join_request(pack_session, pack_id=pack.id, user_id=requester.id)

    app.dependency_overrides[get_current_user] = _override_current_user(member)
    app.dependency_overrides[get_db] = _override_db(pack_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.patch(
                f"/api/packs/{pack.id}/join-requests/{requester.id}",
                json={"status": "approved"},
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 403
    assert response.json() == {"detail": "Not authorized to manage join requests"}


async def test_consensus_join_request_allows_member_votes(pack_session: AsyncSession):
    owner = await _create_user(pack_session, "join-request-vote-owner", "Owner")
    member = await _create_user(pack_session, "join-request-vote-member", "Member")
    requester = await _create_user(pack_session, "join-request-vote-requester", "Requester")
    pack = await _create_pack(
        pack_session,
        creator_id=owner.id,
        name="North Pack",
        created_at=datetime(2025, 1, 2),
        consensus_required=True,
    )
    await _add_member(pack_session, pack_id=pack.id, user_id=owner.id, role=PackMemberRole.ADMIN)
    await _add_member(pack_session, pack_id=pack.id, user_id=member.id)
    await _add_join_request(pack_session, pack_id=pack.id, user_id=requester.id)

    app.dependency_overrides[get_current_user] = _override_current_user(member)
    app.dependency_overrides[get_db] = _override_db(pack_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.patch(
                f"/api/packs/{pack.id}/join-requests/{requester.id}",
                json={"status": "approved"},
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    assert response.json()["status"] == "pending"


async def test_decide_pack_join_request_returns_404_when_request_missing(pack_session: AsyncSession):
    admin = await _create_user(pack_session, "join-request-decide-admin", "Admin")
    requester = await _create_user(pack_session, "join-request-decide-missing-user", "Requester")
    pack = await _create_pack(
        pack_session,
        creator_id=admin.id,
        name="North Pack",
        created_at=datetime(2025, 1, 2),
    )
    await _add_member(pack_session, pack_id=pack.id, user_id=admin.id, role=PackMemberRole.ADMIN)
    await _add_join_request(
        pack_session,
        pack_id=pack.id,
        user_id=requester.id,
        status=PackJoinRequestStatus.DENIED,
    )

    app.dependency_overrides[get_current_user] = _override_current_user(admin)
    app.dependency_overrides[get_db] = _override_db(pack_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.patch(
                f"/api/packs/{pack.id}/join-requests/{requester.id}",
                json={"status": "approved"},
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 404
    assert response.json() == {"detail": "Join request not found"}


async def test_decide_pack_join_request_rejects_pending_as_decision(pack_session: AsyncSession):
    admin = await _create_user(pack_session, "join-request-decide-invalid-admin", "Admin")
    requester = await _create_user(pack_session, "join-request-decide-invalid-requester", "Requester")
    pack = await _create_pack(
        pack_session,
        creator_id=admin.id,
        name="North Pack",
        created_at=datetime(2025, 1, 2),
    )
    await _add_member(pack_session, pack_id=pack.id, user_id=admin.id, role=PackMemberRole.ADMIN)
    await _add_join_request(pack_session, pack_id=pack.id, user_id=requester.id)

    app.dependency_overrides[get_current_user] = _override_current_user(admin)
    app.dependency_overrides[get_db] = _override_db(pack_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.patch(
                f"/api/packs/{pack.id}/join-requests/{requester.id}",
                json={"status": "pending"},
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 422


async def test_decide_pack_join_request_approves_request_and_adds_member(
    pack_session: AsyncSession,
):
    admin = await _create_user(pack_session, "join-request-decide-approve-admin", "Admin")
    requester = await _create_user(
        pack_session,
        "join-request-decide-approve-requester",
        "Requester",
    )
    pack = await _create_pack(
        pack_session,
        creator_id=admin.id,
        name="North Pack",
        created_at=datetime(2025, 1, 2),
    )
    await _add_member(pack_session, pack_id=pack.id, user_id=admin.id, role=PackMemberRole.ADMIN)
    await _add_join_request(pack_session, pack_id=pack.id, user_id=requester.id)

    app.dependency_overrides[get_current_user] = _override_current_user(admin)
    app.dependency_overrides[get_db] = _override_db(pack_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.patch(
                f"/api/packs/{pack.id}/join-requests/{requester.id}",
                json={"status": "approved"},
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert data["pack_id"] == pack.id
    assert data["user_id"] == requester.id
    assert data["status"] == "approved"
    assert data["approvals_required"] == 1
    assert data["approvals_received"] == 1
    assert [vote["decision"] for vote in data["votes"]] == ["approved"]
    assert [vote["voter_user_id"] for vote in data["votes"]] == [admin.id]

    join_request = await pack_session.scalar(
        select(PackJoinRequest).where(
            PackJoinRequest.pack_id == pack.id,
            PackJoinRequest.user_id == requester.id,
        )
    )
    assert join_request is not None
    assert join_request.status == PackJoinRequestStatus.APPROVED

    member = await pack_session.scalar(
        select(PackMember).where(
            PackMember.pack_id == pack.id,
            PackMember.user_id == requester.id,
        )
    )
    assert member is not None
    assert member.role == PackMemberRole.MEMBER

    vote = await pack_session.get(
        PackJoinRequestVote,
        {"join_request_id": join_request.id, "voter_user_id": admin.id},
    )
    assert vote is not None
    assert vote.decision == PackJoinRequestVoteDecision.APPROVED


async def test_decide_pack_join_request_denies_request_without_adding_member(
    pack_session: AsyncSession,
):
    admin = await _create_user(pack_session, "join-request-decide-deny-admin", "Admin")
    requester = await _create_user(pack_session, "join-request-decide-deny-requester", "Requester")
    pack = await _create_pack(
        pack_session,
        creator_id=admin.id,
        name="North Pack",
        created_at=datetime(2025, 1, 2),
    )
    await _add_member(pack_session, pack_id=pack.id, user_id=admin.id, role=PackMemberRole.ADMIN)
    await _add_join_request(pack_session, pack_id=pack.id, user_id=requester.id)

    app.dependency_overrides[get_current_user] = _override_current_user(admin)
    app.dependency_overrides[get_db] = _override_db(pack_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.patch(
                f"/api/packs/{pack.id}/join-requests/{requester.id}",
                json={"status": "denied"},
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "denied"
    assert data["approvals_received"] == 0
    assert [vote["decision"] for vote in data["votes"]] == ["denied"]

    join_request = await pack_session.scalar(
        select(PackJoinRequest).where(
            PackJoinRequest.pack_id == pack.id,
            PackJoinRequest.user_id == requester.id,
        )
    )
    assert join_request is not None
    assert join_request.status == PackJoinRequestStatus.DENIED

    member = await pack_session.scalar(
        select(PackMember).where(
            PackMember.pack_id == pack.id,
            PackMember.user_id == requester.id,
        )
    )
    assert member is None


async def test_consensus_join_request_stays_pending_until_all_members_approve(
    pack_session: AsyncSession,
):
    admin = await _create_user(pack_session, "join-request-consensus-admin", "Admin")
    member = await _create_user(pack_session, "join-request-consensus-member", "Member")
    requester = await _create_user(pack_session, "join-request-consensus-requester", "Requester")
    pack = await _create_pack(
        pack_session,
        creator_id=admin.id,
        name="North Pack",
        created_at=datetime(2025, 1, 2),
        consensus_required=True,
    )
    await _add_member(pack_session, pack_id=pack.id, user_id=admin.id, role=PackMemberRole.ADMIN)
    await _add_member(pack_session, pack_id=pack.id, user_id=member.id)
    await _add_join_request(pack_session, pack_id=pack.id, user_id=requester.id)

    app.dependency_overrides[get_current_user] = _override_current_user(admin)
    app.dependency_overrides[get_db] = _override_db(pack_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            first_response = c.patch(
                f"/api/packs/{pack.id}/join-requests/{requester.id}",
                json={"status": "approved"},
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert first_response.status_code == 200
    first_data = first_response.json()
    assert first_data["status"] == "pending"
    assert first_data["approvals_required"] == 2
    assert first_data["approvals_received"] == 1
    assert [vote["voter_user_id"] for vote in first_data["votes"]] == [admin.id]

    member_record = await pack_session.scalar(
        select(PackMember).where(
            PackMember.pack_id == pack.id,
            PackMember.user_id == requester.id,
        )
    )
    assert member_record is None

    app.dependency_overrides[get_current_user] = _override_current_user(member)
    app.dependency_overrides[get_db] = _override_db(pack_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            second_response = c.patch(
                f"/api/packs/{pack.id}/join-requests/{requester.id}",
                json={"status": "approved"},
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert second_response.status_code == 200
    second_data = second_response.json()
    assert second_data["status"] == "approved"
    assert second_data["approvals_required"] == 2
    assert second_data["approvals_received"] == 2
    assert [vote["voter_user_id"] for vote in second_data["votes"]] == [admin.id, member.id]

    join_request = await pack_session.scalar(
        select(PackJoinRequest).where(
            PackJoinRequest.pack_id == pack.id,
            PackJoinRequest.user_id == requester.id,
        )
    )
    assert join_request is not None
    assert join_request.status == PackJoinRequestStatus.APPROVED

    member_record = await pack_session.scalar(
        select(PackMember).where(
            PackMember.pack_id == pack.id,
            PackMember.user_id == requester.id,
        )
    )
    assert member_record is not None
    assert member_record.role == PackMemberRole.MEMBER


async def test_consensus_join_request_denial_records_vote_and_ends_request(
    pack_session: AsyncSession,
):
    admin = await _create_user(pack_session, "join-request-consensus-deny-admin", "Admin")
    member = await _create_user(pack_session, "join-request-consensus-deny-member", "Member")
    requester = await _create_user(
        pack_session,
        "join-request-consensus-deny-requester",
        "Requester",
    )
    pack = await _create_pack(
        pack_session,
        creator_id=admin.id,
        name="North Pack",
        created_at=datetime(2025, 1, 2),
        consensus_required=True,
    )
    await _add_member(pack_session, pack_id=pack.id, user_id=admin.id, role=PackMemberRole.ADMIN)
    await _add_member(pack_session, pack_id=pack.id, user_id=member.id)
    await _add_join_request(pack_session, pack_id=pack.id, user_id=requester.id)

    app.dependency_overrides[get_current_user] = _override_current_user(member)
    app.dependency_overrides[get_db] = _override_db(pack_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.patch(
                f"/api/packs/{pack.id}/join-requests/{requester.id}",
                json={"status": "denied"},
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "denied"
    assert data["approvals_required"] == 2
    assert data["approvals_received"] == 0
    assert [vote["decision"] for vote in data["votes"]] == ["denied"]

    join_request = await pack_session.scalar(
        select(PackJoinRequest).where(
            PackJoinRequest.pack_id == pack.id,
            PackJoinRequest.user_id == requester.id,
        )
    )
    assert join_request is not None
    assert join_request.status == PackJoinRequestStatus.DENIED


async def test_decide_pack_join_request_rejects_approval_when_pack_is_full(
    pack_session: AsyncSession,
):
    admin = await _create_user(pack_session, "join-request-full-admin", "Admin")
    existing_member = await _create_user(pack_session, "join-request-full-member", "Member")
    requester = await _create_user(pack_session, "join-request-full-requester", "Requester")
    pack = await _create_pack(
        pack_session,
        creator_id=admin.id,
        name="North Pack",
        created_at=datetime(2025, 1, 2),
        max_size=2,
    )
    await _add_member(pack_session, pack_id=pack.id, user_id=admin.id, role=PackMemberRole.ADMIN)
    await _add_member(pack_session, pack_id=pack.id, user_id=existing_member.id)
    await _add_join_request(pack_session, pack_id=pack.id, user_id=requester.id)

    app.dependency_overrides[get_current_user] = _override_current_user(admin)
    app.dependency_overrides[get_db] = _override_db(pack_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.patch(
                f"/api/packs/{pack.id}/join-requests/{requester.id}",
                json={"status": "approved"},
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 409
    assert response.json() == {"detail": "Pack is already full"}

    join_request = await pack_session.scalar(
        select(PackJoinRequest).where(
            PackJoinRequest.pack_id == pack.id,
            PackJoinRequest.user_id == requester.id,
        )
    )
    assert join_request is not None
    assert join_request.status == PackJoinRequestStatus.PENDING

    member = await pack_session.scalar(
        select(PackMember).where(
            PackMember.pack_id == pack.id,
            PackMember.user_id == requester.id,
        )
    )
    assert member is None

    votes = (
        await pack_session.execute(
            select(PackJoinRequestVote).where(PackJoinRequestVote.join_request_id == join_request.id)
        )
    ).scalars().all()
    assert votes == []
