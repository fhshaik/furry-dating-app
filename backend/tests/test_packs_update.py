"""Tests for PATCH /api/packs/{id} endpoint."""

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
    image_url: str | None = None,
    species_tags: list[str] | None = None,
    max_size: int = 10,
    consensus_required: bool = False,
    is_open: bool = True,
    created_at: datetime,
) -> Pack:
    pack = Pack(
        creator_id=creator_id,
        name=name,
        description=description,
        image_url=image_url,
        species_tags=species_tags,
        max_size=max_size,
        consensus_required=consensus_required,
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


def test_update_pack_requires_auth(client: TestClient):
    response = client.patch("/api/packs/1", json={"name": "Updated Pack"})

    assert response.status_code == 401


async def test_update_pack_returns_404_when_missing(pack_session: AsyncSession):
    current_user = await _create_user(pack_session, "pack-update-missing", "Admin")

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(pack_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.patch("/api/packs/999", json={"name": "Ghost Pack"})
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 404
    assert response.json() == {"detail": "Pack not found"}


async def test_update_pack_requires_admin_membership(pack_session: AsyncSession):
    creator = await _create_user(pack_session, "pack-update-creator", "Creator")
    current_user = await _create_user(pack_session, "pack-update-member", "Member")
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
            response = c.patch(f"/api/packs/{pack.id}", json={"name": "Updated Pack"})
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 403
    assert response.json() == {"detail": "Not authorized to update this pack"}


async def test_update_pack_updates_selected_fields(pack_session: AsyncSession):
    current_user = await _create_user(pack_session, "pack-update-admin", "Admin")
    pack = await _create_pack(
        pack_session,
        creator_id=current_user.id,
        name="North Pack",
        description="Original description",
        image_url="https://example.com/original.png",
        species_tags=["wolf"],
        max_size=8,
        consensus_required=False,
        is_open=True,
        created_at=datetime(2025, 1, 3),
    )
    await _add_member(pack_session, pack_id=pack.id, user_id=current_user.id, role=PackMemberRole.ADMIN)

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(pack_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.patch(
                f"/api/packs/{pack.id}",
                json={
                    "name": "Aurora Pack",
                    "description": "Updated description",
                    "image_url": None,
                    "species_tags": ["wolf", "fox"],
                    "max_size": 12,
                    "consensus_required": True,
                    "is_open": False,
                },
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == pack.id
    assert data["name"] == "Aurora Pack"
    assert data["description"] == "Updated description"
    assert data["image_url"] is None
    assert data["species_tags"] == ["wolf", "fox"]
    assert data["max_size"] == 12
    assert data["consensus_required"] is True
    assert data["is_open"] is False


async def test_update_pack_trims_strings_and_species_tags(pack_session: AsyncSession):
    current_user = await _create_user(pack_session, "pack-update-trim-admin", "Admin")
    pack = await _create_pack(
        pack_session,
        creator_id=current_user.id,
        name="North Pack",
        description="Original description",
        image_url="https://example.com/original.png",
        species_tags=["wolf"],
        created_at=datetime(2025, 1, 3),
    )
    await _add_member(pack_session, pack_id=pack.id, user_id=current_user.id, role=PackMemberRole.ADMIN)

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(pack_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.patch(
                f"/api/packs/{pack.id}",
                json={
                    "name": "  Aurora Pack  ",
                    "description": "   ",
                    "image_url": "   ",
                    "species_tags": [" wolf ", "fox", "   "],
                },
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Aurora Pack"
    assert data["description"] is None
    assert data["image_url"] is None
    assert data["species_tags"] == ["wolf", "fox"]


async def test_update_pack_empty_body_is_noop(pack_session: AsyncSession):
    current_user = await _create_user(pack_session, "pack-update-noop", "Admin")
    pack = await _create_pack(
        pack_session,
        creator_id=current_user.id,
        name="North Pack",
        description="Original description",
        created_at=datetime(2025, 1, 3),
    )
    await _add_member(pack_session, pack_id=pack.id, user_id=current_user.id, role=PackMemberRole.ADMIN)

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(pack_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.patch(f"/api/packs/{pack.id}", json={})
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "North Pack"
    assert data["description"] == "Original description"


async def test_update_pack_rejects_null_name(pack_session: AsyncSession):
    current_user = await _create_user(pack_session, "pack-update-null-name", "Admin")
    pack = await _create_pack(
        pack_session,
        creator_id=current_user.id,
        name="North Pack",
        created_at=datetime(2025, 1, 3),
    )
    await _add_member(pack_session, pack_id=pack.id, user_id=current_user.id, role=PackMemberRole.ADMIN)

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(pack_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.patch(f"/api/packs/{pack.id}", json={"name": None})
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 422
    assert response.json() == {"detail": "name cannot be null"}


async def test_update_pack_rejects_max_size_below_current_member_count(
    pack_session: AsyncSession,
):
    current_user = await _create_user(pack_session, "pack-update-max-size-admin", "Admin")
    member = await _create_user(pack_session, "pack-update-max-size-member", "Member")
    pack = await _create_pack(
        pack_session,
        creator_id=current_user.id,
        name="North Pack",
        max_size=3,
        created_at=datetime(2025, 1, 3),
    )
    await _add_member(pack_session, pack_id=pack.id, user_id=current_user.id, role=PackMemberRole.ADMIN)
    await _add_member(pack_session, pack_id=pack.id, user_id=member.id)

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(pack_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.patch(f"/api/packs/{pack.id}", json={"max_size": 1})
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 400
    assert response.json() == {"detail": "max_size cannot be less than current member count"}
