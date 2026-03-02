"""Tests for the User ORM model."""

import pytest
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.user import User


# ---------------------------------------------------------------------------
# Schema / column structure tests (no DB connection needed)
# ---------------------------------------------------------------------------


def test_user_tablename():
    assert User.__tablename__ == "users"


def test_user_has_required_columns():
    mapper = inspect(User)
    column_names = {col.key for col in mapper.columns}
    assert "oauth_provider" in column_names
    assert "oauth_id" in column_names
    assert "email" in column_names
    assert "display_name" in column_names
    assert "bio" in column_names
    assert "age" in column_names
    assert "city" in column_names
    assert "nsfw_enabled" in column_names
    assert "relationship_style" in column_names


def test_oauth_provider_column_type():
    col = User.__table__.c["oauth_provider"]
    assert col.type.length == 32
    assert not col.nullable


def test_oauth_id_column_type():
    col = User.__table__.c["oauth_id"]
    assert col.type.length == 255
    assert not col.nullable


def test_email_column_is_optional():
    col = User.__table__.c["email"]
    assert col.nullable


def test_display_name_column_type():
    col = User.__table__.c["display_name"]
    assert col.type.length == 100
    assert not col.nullable


def test_unique_constraint_on_oauth_provider_and_id():
    constraints = {c.name for c in User.__table__.constraints}
    assert "uq_users_oauth" in constraints


def test_primary_key_is_id():
    pk_cols = [col.name for col in User.__table__.primary_key]
    assert pk_cols == ["id"]


# ---------------------------------------------------------------------------
# In-memory SQLite tests (verify create/read round-trip)
# ---------------------------------------------------------------------------


@pytest.fixture()
async def sqlite_session():
    """Provide an in-memory SQLite async session with the users table created."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


async def test_create_user_minimal(sqlite_session: AsyncSession):
    """A user with only required fields can be saved and retrieved."""
    user = User(oauth_provider="google", oauth_id="g-001", display_name="Foxy")
    sqlite_session.add(user)
    await sqlite_session.commit()
    await sqlite_session.refresh(user)

    assert user.id is not None
    assert user.oauth_provider == "google"
    assert user.oauth_id == "g-001"
    assert user.display_name == "Foxy"
    assert user.email is None


async def test_create_user_with_email(sqlite_session: AsyncSession):
    """Email field is stored and retrieved correctly."""
    user = User(
        oauth_provider="discord",
        oauth_id="d-007",
        email="wolf@example.com",
        display_name="Wolfy",
    )
    sqlite_session.add(user)
    await sqlite_session.commit()
    await sqlite_session.refresh(user)

    assert user.email == "wolf@example.com"


async def test_user_defaults(sqlite_session: AsyncSession):
    """nsfw_enabled defaults to False; created_at is set automatically."""
    user = User(oauth_provider="google", oauth_id="g-002", display_name="Bear")
    sqlite_session.add(user)
    await sqlite_session.commit()
    await sqlite_session.refresh(user)

    assert user.nsfw_enabled is False
    assert user.created_at is not None


def test_relationship_style_column_is_optional():
    col = User.__table__.c["relationship_style"]
    assert col.nullable
    assert col.type.length == 50


async def test_profile_fields_stored_and_retrieved(sqlite_session: AsyncSession):
    """bio, age, city, nsfw_enabled, and relationship_style are persisted correctly."""
    user = User(
        oauth_provider="google",
        oauth_id="g-100",
        display_name="Fennec",
        bio="Desert wanderer",
        age=25,
        city="Phoenix",
        nsfw_enabled=True,
        relationship_style="polyamorous",
    )
    sqlite_session.add(user)
    await sqlite_session.commit()
    await sqlite_session.refresh(user)

    assert user.bio == "Desert wanderer"
    assert user.age == 25
    assert user.city == "Phoenix"
    assert user.nsfw_enabled is True
    assert user.relationship_style == "polyamorous"


async def test_relationship_style_defaults_to_none(sqlite_session: AsyncSession):
    """relationship_style is None when not provided."""
    user = User(oauth_provider="google", oauth_id="g-101", display_name="Lynx")
    sqlite_session.add(user)
    await sqlite_session.commit()
    await sqlite_session.refresh(user)

    assert user.relationship_style is None


async def test_oauth_provider_and_id_unique(sqlite_session: AsyncSession):
    """Inserting two users with the same (oauth_provider, oauth_id) must fail."""
    from sqlalchemy.exc import IntegrityError

    user1 = User(oauth_provider="google", oauth_id="dup-01", display_name="Alpha")
    user2 = User(oauth_provider="google", oauth_id="dup-01", display_name="Beta")
    sqlite_session.add(user1)
    await sqlite_session.commit()

    sqlite_session.add(user2)
    with pytest.raises(IntegrityError):
        await sqlite_session.commit()
