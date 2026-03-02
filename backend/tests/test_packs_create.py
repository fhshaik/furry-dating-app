"""Tests for POST /api/packs endpoint."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.deps import get_current_user
from app.database import Base, get_db
from app.main import app
from app.models.conversation import Conversation, ConversationType
from app.models.conversation_member import ConversationMember
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


def test_create_pack_requires_auth(client: TestClient):
    response = client.post("/api/packs", json={"name": "North Pack"})

    assert response.status_code == 401


async def test_create_pack_requires_name(pack_session: AsyncSession):
    current_user = await _create_user(pack_session, "pack-missing-name", "Creator")

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(pack_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.post("/api/packs", json={})
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 422


async def test_create_pack_creates_admin_membership(pack_session: AsyncSession):
    current_user = await _create_user(pack_session, "pack-creator-minimal", "Creator")

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(pack_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.post("/api/packs", json={"name": "North Pack"})
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 201
    data = response.json()
    assert data["creator_id"] == current_user.id
    assert data["name"] == "North Pack"
    assert data["description"] is None
    assert data["image_url"] is None
    assert data["species_tags"] is None
    assert data["max_size"] == 10
    assert data["consensus_required"] is False
    assert data["is_open"] is True

    packs = (await pack_session.execute(select(Pack))).scalars().all()
    assert len(packs) == 1

    memberships = (await pack_session.execute(select(PackMember))).scalars().all()
    assert len(memberships) == 1
    assert memberships[0].pack_id == packs[0].id
    assert memberships[0].user_id == current_user.id
    assert memberships[0].role == PackMemberRole.ADMIN


async def test_create_pack_creates_pack_conversation(pack_session: AsyncSession):
    current_user = await _create_user(pack_session, "pack-conv-creator", "Creator")

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(pack_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.post("/api/packs", json={"name": "Wolf Pack"})
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 201
    pack_id = response.json()["id"]

    conversations = (await pack_session.execute(select(Conversation))).scalars().all()
    assert len(conversations) == 1
    assert conversations[0].type == ConversationType.PACK
    assert conversations[0].pack_id == pack_id

    members = (await pack_session.execute(select(ConversationMember))).scalars().all()
    assert len(members) == 1
    assert members[0].conversation_id == conversations[0].id
    assert members[0].user_id == current_user.id


async def test_create_pack_supports_optional_fields(pack_session: AsyncSession):
    current_user = await _create_user(pack_session, "pack-creator-full", "Founder")

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(pack_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.post(
                "/api/packs",
                json={
                    "name": "Aurora Pack",
                    "description": "A social circle for snowy nights.",
                    "image_url": "https://example.com/aurora-pack.png",
                    "species_tags": ["wolf", "fox"],
                    "max_size": 6,
                    "consensus_required": True,
                    "is_open": False,
                },
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 201
    data = response.json()
    assert data["creator_id"] == current_user.id
    assert data["name"] == "Aurora Pack"
    assert data["description"] == "A social circle for snowy nights."
    assert data["image_url"] == "https://example.com/aurora-pack.png"
    assert data["species_tags"] == ["wolf", "fox"]
    assert data["max_size"] == 6
    assert data["consensus_required"] is True
    assert data["is_open"] is False


async def test_create_pack_trims_strings_and_species_tags(pack_session: AsyncSession):
    current_user = await _create_user(pack_session, "pack-creator-trimmed", "Founder")

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(pack_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.post(
                "/api/packs",
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

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Aurora Pack"
    assert data["description"] is None
    assert data["image_url"] is None
    assert data["species_tags"] == ["wolf", "fox"]
