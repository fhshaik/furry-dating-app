"""Tests for GET /api/packs/mine endpoint."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.deps import get_current_user
from app.database import Base, get_db
from app.main import app
from app.models.pack import Pack
from app.models.pack_member import PackMember, PackMemberRole
from app.models.user import User


@pytest.fixture()
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as s:
        yield s

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


def test_list_my_packs_requires_auth(client: TestClient):
    response = client.get("/api/packs/mine")

    assert response.status_code == 401


async def test_list_my_packs_only_returns_joined_packs(session: AsyncSession):
    current_user = await _create_user(session, "mine-current", "Current")
    other_user = await _create_user(session, "mine-other", "Other")

    joined_pack = await _create_pack(
        session,
        creator_id=other_user.id,
        name="Joined Pack",
        created_at=datetime(2025, 1, 2),
    )
    not_joined_pack = await _create_pack(
        session,
        creator_id=other_user.id,
        name="Not Joined Pack",
        created_at=datetime(2025, 1, 1),
    )
    await _add_member(session, pack_id=joined_pack.id, user_id=current_user.id)

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.get("/api/packs/mine")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["page"] == 1
    assert data["limit"] == 20
    assert data["has_more"] is False
    assert [item["id"] for item in data["items"]] == [joined_pack.id]
    assert all(item["id"] != not_joined_pack.id for item in data["items"])


async def test_list_my_packs_includes_closed_packs(session: AsyncSession):
    current_user = await _create_user(session, "mine-closed-current", "Current")
    creator = await _create_user(session, "mine-closed-creator", "Creator")

    closed_joined_pack = await _create_pack(
        session,
        creator_id=creator.id,
        name="Closed Joined Pack",
        is_open=False,
        created_at=datetime(2025, 1, 1),
    )
    await _add_member(session, pack_id=closed_joined_pack.id, user_id=current_user.id)

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.get("/api/packs/mine")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == closed_joined_pack.id


async def test_list_my_packs_includes_member_count(session: AsyncSession):
    current_user = await _create_user(session, "mine-count-current", "Current")
    other_user = await _create_user(session, "mine-count-other", "Other")
    creator = await _create_user(session, "mine-count-creator", "Creator")

    pack = await _create_pack(
        session,
        creator_id=creator.id,
        name="Count Pack",
        created_at=datetime(2025, 1, 1),
    )
    await _add_member(session, pack_id=pack.id, user_id=current_user.id)
    await _add_member(session, pack_id=pack.id, user_id=other_user.id)

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.get("/api/packs/mine")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["member_count"] == 2


async def test_list_my_packs_paginates_results(session: AsyncSession):
    current_user = await _create_user(session, "mine-page-current", "Current")
    creator = await _create_user(session, "mine-page-creator", "Creator")

    first_pack = await _create_pack(
        session,
        creator_id=creator.id,
        name="First Pack",
        created_at=datetime(2025, 1, 1),
    )
    second_pack = await _create_pack(
        session,
        creator_id=creator.id,
        name="Second Pack",
        created_at=datetime(2025, 1, 2),
    )
    third_pack = await _create_pack(
        session,
        creator_id=creator.id,
        name="Third Pack",
        created_at=datetime(2025, 1, 3),
    )
    await _add_member(session, pack_id=first_pack.id, user_id=current_user.id)
    await _add_member(session, pack_id=second_pack.id, user_id=current_user.id)
    await _add_member(session, pack_id=third_pack.id, user_id=current_user.id)

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.get("/api/packs/mine?page=2&limit=1")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 2
    assert data["limit"] == 1
    assert data["total"] == 3
    assert data["has_more"] is True
    assert [item["id"] for item in data["items"]] == [second_pack.id]


async def test_list_my_packs_empty_when_no_memberships(session: AsyncSession):
    current_user = await _create_user(session, "mine-empty-current", "Current")
    creator = await _create_user(session, "mine-empty-creator", "Creator")

    await _create_pack(
        session,
        creator_id=creator.id,
        name="Some Pack",
        created_at=datetime(2025, 1, 1),
    )

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.get("/api/packs/mine")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []
    assert data["has_more"] is False
