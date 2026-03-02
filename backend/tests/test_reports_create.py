"""Tests for POST /api/reports endpoints."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.deps import get_current_user
from app.database import Base, get_db
from app.main import app
from app.models.conversation import Conversation, ConversationType
from app.models.fursona import Fursona
from app.models.message import Message
from app.models.pack import Pack
from app.models.report import Report
from app.models.user import User


@pytest.fixture()
async def reports_session():
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


async def _create_pack(session: AsyncSession, creator_id: int, name: str) -> Pack:
    pack = Pack(creator_id=creator_id, name=name)
    session.add(pack)
    await session.commit()
    await session.refresh(pack)
    return pack


async def _create_fursona(session: AsyncSession, user_id: int, name: str) -> Fursona:
    fursona = Fursona(
        user_id=user_id,
        name=name,
        species="Wolf",
        description="A friendly wolf",
    )
    session.add(fursona)
    await session.commit()
    await session.refresh(fursona)
    return fursona


async def _create_message(session: AsyncSession, sender_id: int, content: str) -> Message:
    conversation = Conversation(type=ConversationType.DIRECT)
    session.add(conversation)
    await session.commit()
    await session.refresh(conversation)

    message = Message(
        conversation_id=conversation.id,
        sender_id=sender_id,
        content=content,
    )
    session.add(message)
    await session.commit()
    await session.refresh(message)
    return message


def test_create_user_report_requires_auth(client: TestClient):
    response = client.post(
        "/api/reports/users",
        json={"reported_user_id": 2, "reason": "Harassment"},
    )

    assert response.status_code == 401


async def test_create_user_report_persists_report(reports_session: AsyncSession):
    reporter = await _create_user(reports_session, "reporter-user", "Reporter")
    reported_user = await _create_user(reports_session, "reported-user", "Reported")

    app.dependency_overrides[get_current_user] = _override_current_user(reporter)
    app.dependency_overrides[get_db] = _override_db(reports_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.post(
                "/api/reports/users",
                json={
                    "reported_user_id": reported_user.id,
                    "reason": "  Harassment  ",
                    "details": "  Repeated abusive messages  ",
                },
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 201
    data = response.json()
    assert data["reporter_id"] == reporter.id
    assert data["reported_user_id"] == reported_user.id
    assert data["content_type"] is None
    assert data["content_id"] is None
    assert data["reason"] == "Harassment"
    assert data["details"] == "Repeated abusive messages"

    reports = (await reports_session.execute(select(Report))).scalars().all()
    assert len(reports) == 1
    assert reports[0].reported_user_id == reported_user.id


async def test_create_user_report_rejects_self_report(reports_session: AsyncSession):
    reporter = await _create_user(reports_session, "self-report-user", "Reporter")

    app.dependency_overrides[get_current_user] = _override_current_user(reporter)
    app.dependency_overrides[get_db] = _override_db(reports_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.post(
                "/api/reports/users",
                json={"reported_user_id": reporter.id, "reason": "Spam"},
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 400
    assert response.json() == {"detail": "You cannot report yourself"}


async def test_create_content_report_persists_report_for_fursona(
    reports_session: AsyncSession,
):
    reporter = await _create_user(reports_session, "content-reporter", "Reporter")
    content_owner = await _create_user(reports_session, "content-owner", "Owner")
    fursona = await _create_fursona(reports_session, content_owner.id, "Nova")

    app.dependency_overrides[get_current_user] = _override_current_user(reporter)
    app.dependency_overrides[get_db] = _override_db(reports_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.post(
                "/api/reports/content",
                json={
                    "content_type": "fursona",
                    "content_id": fursona.id,
                    "reason": "Explicit content",
                    "details": "   ",
                },
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 201
    data = response.json()
    assert data["reporter_id"] == reporter.id
    assert data["reported_user_id"] is None
    assert data["content_type"] == "fursona"
    assert data["content_id"] == fursona.id
    assert data["reason"] == "Explicit content"
    assert data["details"] is None

    reports = (await reports_session.execute(select(Report))).scalars().all()
    assert len(reports) == 1
    assert reports[0].content_type == "fursona"


async def test_create_content_report_returns_404_for_missing_target(
    reports_session: AsyncSession,
):
    reporter = await _create_user(reports_session, "missing-content-reporter", "Reporter")

    app.dependency_overrides[get_current_user] = _override_current_user(reporter)
    app.dependency_overrides[get_db] = _override_db(reports_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.post(
                "/api/reports/content",
                json={
                    "content_type": "pack",
                    "content_id": 999,
                    "reason": "Spam",
                },
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 404
    assert response.json() == {"detail": "Reported content not found"}


async def test_create_content_report_rejects_unknown_content_type(
    reports_session: AsyncSession,
):
    reporter = await _create_user(reports_session, "unknown-type-reporter", "Reporter")

    app.dependency_overrides[get_current_user] = _override_current_user(reporter)
    app.dependency_overrides[get_db] = _override_db(reports_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.post(
                "/api/reports/content",
                json={
                    "content_type": "post",
                    "content_id": 1,
                    "reason": "Spam",
                },
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 422


async def test_create_content_report_supports_message_target(reports_session: AsyncSession):
    reporter = await _create_user(reports_session, "message-reporter", "Reporter")
    sender = await _create_user(reports_session, "message-sender", "Sender")
    message = await _create_message(reports_session, sender.id, "Not acceptable")

    app.dependency_overrides[get_current_user] = _override_current_user(reporter)
    app.dependency_overrides[get_db] = _override_db(reports_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.post(
                "/api/reports/content",
                json={
                    "content_type": "message",
                    "content_id": message.id,
                    "reason": "Harassment",
                },
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 201
    assert response.json()["content_type"] == "message"


async def test_create_content_report_supports_pack_target(reports_session: AsyncSession):
    reporter = await _create_user(reports_session, "pack-reporter", "Reporter")
    creator = await _create_user(reports_session, "pack-owner", "Owner")
    pack = await _create_pack(reports_session, creator.id, "Moon Pack")

    app.dependency_overrides[get_current_user] = _override_current_user(reporter)
    app.dependency_overrides[get_db] = _override_db(reports_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.post(
                "/api/reports/content",
                json={
                    "content_type": "pack",
                    "content_id": pack.id,
                    "reason": "Hate speech",
                },
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 201
    assert response.json()["content_id"] == pack.id
