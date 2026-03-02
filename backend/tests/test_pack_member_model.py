"""Tests for the PackMember ORM model."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.pack import Pack
from app.models.pack_member import PackMember, PackMemberRole
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


def test_pack_member_tablename():
    assert PackMember.__tablename__ == "pack_members"


def test_pack_member_has_required_columns():
    column_names = set(PackMember.__table__.c.keys())
    assert "pack_id" in column_names
    assert "user_id" in column_names
    assert "role" in column_names
    assert "joined_at" in column_names


async def test_create_pack_member_uses_default_role(sqlite_session: AsyncSession):
    creator = User(oauth_provider="google", oauth_id="pack-member-creator", display_name="Creator")
    member = User(oauth_provider="google", oauth_id="pack-member-user", display_name="Member")
    sqlite_session.add_all([creator, member])
    await sqlite_session.commit()

    pack = Pack(creator_id=creator.id, name="North Pack")
    sqlite_session.add(pack)
    await sqlite_session.commit()

    pack_member = PackMember(pack_id=pack.id, user_id=member.id)
    sqlite_session.add(pack_member)
    await sqlite_session.commit()
    await sqlite_session.refresh(pack_member)

    assert pack_member.role == PackMemberRole.MEMBER
    assert pack_member.joined_at is not None


async def test_create_pack_member_with_admin_role(sqlite_session: AsyncSession):
    creator = User(oauth_provider="discord", oauth_id="pack-admin-creator", display_name="Founder")
    member = User(oauth_provider="discord", oauth_id="pack-admin-user", display_name="Admin")
    sqlite_session.add_all([creator, member])
    await sqlite_session.commit()

    pack = Pack(creator_id=creator.id, name="Aurora Pack")
    sqlite_session.add(pack)
    await sqlite_session.commit()

    pack_member = PackMember(
        pack_id=pack.id,
        user_id=member.id,
        role=PackMemberRole.ADMIN,
    )
    sqlite_session.add(pack_member)
    await sqlite_session.commit()
    await sqlite_session.refresh(pack_member)

    assert pack_member.role == PackMemberRole.ADMIN
