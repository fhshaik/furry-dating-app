"""Tests for GET /api/packs/{id}/join-requests endpoint."""

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
    created_at: datetime,
    status: PackJoinRequestStatus = PackJoinRequestStatus.PENDING,
) -> None:
    session.add(
        PackJoinRequest(
            pack_id=pack_id,
            user_id=user_id,
            status=status,
            created_at=created_at,
        )
    )
    await session.commit()


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


def test_list_pack_join_requests_requires_auth(client: TestClient):
    response = client.get("/api/packs/1/join-requests")

    assert response.status_code == 401


async def test_list_pack_join_requests_returns_404_when_pack_missing(pack_session: AsyncSession):
    current_user = await _create_user(pack_session, "join-requests-missing-admin", "Admin")

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(pack_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.get("/api/packs/999/join-requests")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 404
    assert response.json() == {"detail": "Pack not found"}


async def test_list_pack_join_requests_requires_admin_membership(pack_session: AsyncSession):
    creator = await _create_user(pack_session, "join-requests-owner", "Owner")
    current_user = await _create_user(pack_session, "join-requests-member", "Member")
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
            response = c.get(f"/api/packs/{pack.id}/join-requests")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 403
    assert response.json() == {"detail": "Not authorized to view join requests"}


async def test_list_pack_join_requests_returns_pending_requests_for_admin(
    pack_session: AsyncSession,
):
    admin = await _create_user(pack_session, "join-requests-admin", "Admin")
    first_requester = await _create_user(pack_session, "join-requests-first", "Scout")
    second_requester = await _create_user(pack_session, "join-requests-second", "Howler")
    denied_requester = await _create_user(pack_session, "join-requests-denied", "Denied")
    pack = await _create_pack(
        pack_session,
        creator_id=admin.id,
        name="North Pack",
        created_at=datetime(2025, 1, 3),
    )
    await _add_member(
        pack_session,
        pack_id=pack.id,
        user_id=admin.id,
        role=PackMemberRole.ADMIN,
    )
    await _add_join_request(
        pack_session,
        pack_id=pack.id,
        user_id=second_requester.id,
        created_at=datetime(2025, 1, 5, 12, 0, 0),
    )
    await _add_join_request(
        pack_session,
        pack_id=pack.id,
        user_id=first_requester.id,
        created_at=datetime(2025, 1, 4, 12, 0, 0),
    )
    await _add_join_request(
        pack_session,
        pack_id=pack.id,
        user_id=denied_requester.id,
        created_at=datetime(2025, 1, 6, 12, 0, 0),
        status=PackJoinRequestStatus.DENIED,
    )

    app.dependency_overrides[get_current_user] = _override_current_user(admin)
    app.dependency_overrides[get_db] = _override_db(pack_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.get(f"/api/packs/{pack.id}/join-requests")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert [item["user_id"] for item in data] == [first_requester.id, second_requester.id]
    assert [item["user"]["display_name"] for item in data] == ["Scout", "Howler"]
    assert all(item["status"] == "pending" for item in data)
    assert all(item["pack_id"] == pack.id for item in data)
    assert all(item["approvals_required"] == 1 for item in data)
    assert all(item["approvals_received"] == 0 for item in data)
    assert all(item["votes"] == [] for item in data)


async def test_list_pack_join_requests_allows_members_for_consensus_packs(
    pack_session: AsyncSession,
):
    admin = await _create_user(pack_session, "join-requests-consensus-admin", "Admin")
    member = await _create_user(pack_session, "join-requests-consensus-member", "Member")
    requester = await _create_user(pack_session, "join-requests-consensus-requester", "Requester")
    pack = await _create_pack(
        pack_session,
        creator_id=admin.id,
        name="North Pack",
        created_at=datetime(2025, 1, 3),
        consensus_required=True,
    )
    await _add_member(pack_session, pack_id=pack.id, user_id=admin.id, role=PackMemberRole.ADMIN)
    await _add_member(pack_session, pack_id=pack.id, user_id=member.id)
    await _add_join_request(
        pack_session,
        pack_id=pack.id,
        user_id=requester.id,
        created_at=datetime(2025, 1, 4, 12, 0, 0),
    )
    join_request = await pack_session.scalar(
        select(PackJoinRequest).where(
            PackJoinRequest.pack_id == pack.id,
            PackJoinRequest.user_id == requester.id,
        )
    )
    assert join_request is not None
    await _add_vote(
        pack_session,
        join_request_id=join_request.id,
        voter_user_id=admin.id,
        decision=PackJoinRequestVoteDecision.APPROVED,
    )

    app.dependency_overrides[get_current_user] = _override_current_user(member)
    app.dependency_overrides[get_db] = _override_db(pack_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.get(f"/api/packs/{pack.id}/join-requests")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["user_id"] == requester.id
    assert data[0]["approvals_required"] == 2
    assert data[0]["approvals_received"] == 1
    assert [vote["voter_user_id"] for vote in data[0]["votes"]] == [admin.id]
    assert [vote["decision"] for vote in data[0]["votes"]] == ["approved"]
    assert [vote["user"]["display_name"] for vote in data[0]["votes"]] == ["Admin"]
    assert [vote["user"]["id"] for vote in data[0]["votes"]] == [admin.id]


async def test_list_pack_join_requests_includes_vote_user_details(
    pack_session: AsyncSession,
):
    admin = await _create_user(pack_session, "join-requests-vote-user-admin", "WolfAdmin")
    member = await _create_user(pack_session, "join-requests-vote-user-member", "FoxMember")
    requester = await _create_user(pack_session, "join-requests-vote-user-requester", "BearRequester")
    pack = await _create_pack(
        pack_session,
        creator_id=admin.id,
        name="Consensus Pack",
        created_at=datetime(2025, 1, 3),
        consensus_required=True,
    )
    await _add_member(pack_session, pack_id=pack.id, user_id=admin.id, role=PackMemberRole.ADMIN)
    await _add_member(pack_session, pack_id=pack.id, user_id=member.id)
    await _add_join_request(
        pack_session,
        pack_id=pack.id,
        user_id=requester.id,
        created_at=datetime(2025, 1, 4, 12, 0, 0),
    )
    join_request = await pack_session.scalar(
        select(PackJoinRequest).where(
            PackJoinRequest.pack_id == pack.id,
            PackJoinRequest.user_id == requester.id,
        )
    )
    assert join_request is not None
    await _add_vote(
        pack_session,
        join_request_id=join_request.id,
        voter_user_id=admin.id,
        decision=PackJoinRequestVoteDecision.APPROVED,
    )
    await _add_vote(
        pack_session,
        join_request_id=join_request.id,
        voter_user_id=member.id,
        decision=PackJoinRequestVoteDecision.DENIED,
    )

    app.dependency_overrides[get_current_user] = _override_current_user(admin)
    app.dependency_overrides[get_db] = _override_db(pack_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.get(f"/api/packs/{pack.id}/join-requests")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    votes = data[0]["votes"]
    assert len(votes) == 2
    assert {v["user"]["display_name"] for v in votes} == {"WolfAdmin", "FoxMember"}
    admin_vote = next(v for v in votes if v["voter_user_id"] == admin.id)
    member_vote = next(v for v in votes if v["voter_user_id"] == member.id)
    assert admin_vote["decision"] == "approved"
    assert admin_vote["user"]["display_name"] == "WolfAdmin"
    assert member_vote["decision"] == "denied"
    assert member_vote["user"]["display_name"] == "FoxMember"
