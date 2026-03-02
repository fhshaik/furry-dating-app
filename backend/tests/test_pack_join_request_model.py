"""Tests for the PackJoinRequest ORM model."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.pack import Pack
from app.models.pack_join_request import PackJoinRequest, PackJoinRequestStatus
from app.models.user import User


@pytest.fixture()
async def sqlite_session():
    """Provide an in-memory SQLite async session with required tables created."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


def test_pack_join_request_tablename():
    assert PackJoinRequest.__tablename__ == "pack_join_requests"


def test_pack_join_request_has_required_columns():
    column_names = set(PackJoinRequest.__table__.c.keys())
    assert "id" in column_names
    assert "pack_id" in column_names
    assert "user_id" in column_names
    assert "status" in column_names
    assert "created_at" in column_names


async def test_create_pack_join_request_uses_default_status(sqlite_session: AsyncSession):
    creator = User(
        oauth_provider="google",
        oauth_id="pack-join-request-creator",
        display_name="Creator",
    )
    requester = User(
        oauth_provider="google",
        oauth_id="pack-join-request-user",
        display_name="Requester",
    )
    sqlite_session.add_all([creator, requester])
    await sqlite_session.commit()

    pack = Pack(creator_id=creator.id, name="North Pack")
    sqlite_session.add(pack)
    await sqlite_session.commit()

    pack_join_request = PackJoinRequest(pack_id=pack.id, user_id=requester.id)
    sqlite_session.add(pack_join_request)
    await sqlite_session.commit()
    await sqlite_session.refresh(pack_join_request)

    assert pack_join_request.id is not None
    assert pack_join_request.status == PackJoinRequestStatus.PENDING
    assert pack_join_request.created_at is not None


async def test_create_pack_join_request_with_approved_status(sqlite_session: AsyncSession):
    creator = User(
        oauth_provider="discord",
        oauth_id="approved-pack-join-request-creator",
        display_name="Founder",
    )
    requester = User(
        oauth_provider="discord",
        oauth_id="approved-pack-join-request-user",
        display_name="Requester",
    )
    sqlite_session.add_all([creator, requester])
    await sqlite_session.commit()

    pack = Pack(creator_id=creator.id, name="Aurora Pack")
    sqlite_session.add(pack)
    await sqlite_session.commit()

    pack_join_request = PackJoinRequest(
        pack_id=pack.id,
        user_id=requester.id,
        status=PackJoinRequestStatus.APPROVED,
    )
    sqlite_session.add(pack_join_request)
    await sqlite_session.commit()
    await sqlite_session.refresh(pack_join_request)

    assert pack_join_request.status == PackJoinRequestStatus.APPROVED
