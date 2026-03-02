"""Tests for GET /api/packs/{id} endpoint."""

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
    description: str | None = None,
    species_tags: list[str] | None = None,
    is_open: bool = True,
    created_at: datetime,
) -> Pack:
    pack = Pack(
        creator_id=creator_id,
        name=name,
        description=description,
        species_tags=species_tags,
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
    joined_at: datetime | None = None,
) -> None:
    session.add(
        PackMember(
            pack_id=pack_id,
            user_id=user_id,
            role=role,
            joined_at=joined_at or datetime(2025, 1, 1),
        )
    )
    await session.commit()


def test_get_pack_requires_auth(client: TestClient):
    response = client.get("/api/packs/1")

    assert response.status_code == 401


async def test_get_pack_returns_open_pack_details(pack_session: AsyncSession):
    current_user = await _create_user(pack_session, "pack-detail-viewer", "Viewer")
    creator = await _create_user(pack_session, "pack-detail-creator", "Creator")
    member = await _create_user(pack_session, "pack-detail-member", "Scout")

    pack = await _create_pack(
        pack_session,
        creator_id=creator.id,
        name="North Pack",
        description="A roaming social group.",
        species_tags=["wolf", "fox"],
        created_at=datetime(2025, 1, 3),
    )
    await _add_member(
        pack_session,
        pack_id=pack.id,
        user_id=creator.id,
        role=PackMemberRole.ADMIN,
        joined_at=datetime(2025, 1, 3, 9, 0, 0),
    )
    await _add_member(
        pack_session,
        pack_id=pack.id,
        user_id=member.id,
        joined_at=datetime(2025, 1, 4, 9, 0, 0),
    )

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(pack_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.get(f"/api/packs/{pack.id}")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == pack.id
    assert data["name"] == "North Pack"
    assert data["description"] == "A roaming social group."
    assert data["species_tags"] == ["wolf", "fox"]
    assert [member_item["user"]["display_name"] for member_item in data["members"]] == [
        "Creator",
        "Scout",
    ]
    assert [member_item["role"] for member_item in data["members"]] == ["admin", "member"]


async def test_get_pack_allows_closed_pack_members(pack_session: AsyncSession):
    creator = await _create_user(pack_session, "pack-detail-closed-creator", "Creator")
    current_user = await _create_user(pack_session, "pack-detail-closed-member", "Member")

    pack = await _create_pack(
        pack_session,
        creator_id=creator.id,
        name="Private Pack",
        is_open=False,
        created_at=datetime(2025, 1, 3),
    )
    await _add_member(
        pack_session,
        pack_id=pack.id,
        user_id=creator.id,
        role=PackMemberRole.ADMIN,
        joined_at=datetime(2025, 1, 3, 9, 0, 0),
    )
    await _add_member(
        pack_session,
        pack_id=pack.id,
        user_id=current_user.id,
        joined_at=datetime(2025, 1, 4, 9, 0, 0),
    )

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(pack_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.get(f"/api/packs/{pack.id}")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    assert response.json()["id"] == pack.id


async def test_get_pack_hides_closed_pack_from_non_member(pack_session: AsyncSession):
    creator = await _create_user(pack_session, "pack-detail-secret-creator", "Creator")
    current_user = await _create_user(pack_session, "pack-detail-secret-viewer", "Viewer")

    pack = await _create_pack(
        pack_session,
        creator_id=creator.id,
        name="Secret Pack",
        is_open=False,
        created_at=datetime(2025, 1, 3),
    )
    await _add_member(
        pack_session,
        pack_id=pack.id,
        user_id=creator.id,
        role=PackMemberRole.ADMIN,
        joined_at=datetime(2025, 1, 3, 9, 0, 0),
    )

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(pack_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.get(f"/api/packs/{pack.id}")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 404
    assert response.json() == {"detail": "Pack not found"}


async def test_get_pack_returns_404_when_missing(pack_session: AsyncSession):
    current_user = await _create_user(pack_session, "pack-detail-missing", "Viewer")

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(pack_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.get("/api/packs/999")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 404
    assert response.json() == {"detail": "Pack not found"}
