"""Tests for GET /api/discover endpoint."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.deps import get_current_user
from app.database import Base, get_db
from app.models.fursona import Fursona
from app.main import app
from app.models.match import Match
from app.models.swipe import Swipe, SwipeAction
from app.models.user import User


@pytest.fixture()
async def discover_session():
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


async def _create_user(session: AsyncSession, user_id: str, display_name: str) -> User:
    user = User(
        oauth_provider="google",
        oauth_id=user_id,
        email=f"{user_id}@example.com",
        display_name=display_name,
        bio=f"{display_name} bio",
        age=25,
        city="Seattle",
        relationship_style="polyamorous",
        created_at=datetime(2025, 1, 1),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def _create_fursona(
    session: AsyncSession,
    *,
    user_id: int,
    name: str,
    species: str,
    is_primary: bool = True,
    is_nsfw: bool = False,
) -> Fursona:
    fursona = Fursona(
        user_id=user_id,
        name=name,
        species=species,
        is_primary=is_primary,
        is_nsfw=is_nsfw,
    )
    session.add(fursona)
    await session.commit()
    await session.refresh(fursona)
    return fursona


def test_list_discover_requires_auth(client: TestClient):
    response = client.get("/api/discover")

    assert response.status_code == 401


async def test_list_discover_excludes_self_seen_and_existing_matches(discover_session: AsyncSession):
    current_user = await _create_user(discover_session, "current-user", "Current")
    seen_user = await _create_user(discover_session, "seen-user", "Seen")
    matched_user = await _create_user(discover_session, "matched-user", "Matched")
    unmatched_user = await _create_user(discover_session, "unmatched-user", "Unmatched")
    available_user = await _create_user(discover_session, "available-user", "Available")

    discover_session.add(
        Swipe(
            swiper_id=current_user.id,
            target_user_id=seen_user.id,
            action=SwipeAction.PASS,
        )
    )
    discover_session.add(
        Match(
            user_a_id=current_user.id,
            user_b_id=matched_user.id,
        )
    )
    discover_session.add(
        Match(
            user_a_id=current_user.id,
            user_b_id=unmatched_user.id,
            unmatched_at=datetime(2025, 2, 1),
        )
    )
    await discover_session.commit()

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(discover_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.get("/api/discover")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["limit"] == 20
    assert data["total"] == 2
    assert data["has_more"] is False
    assert [item["id"] for item in data["items"]] == [available_user.id, unmatched_user.id]
    assert all(item["id"] != current_user.id for item in data["items"])
    assert all(item["id"] != seen_user.id for item in data["items"])
    assert all(item["id"] != matched_user.id for item in data["items"])
    assert "email" not in data["items"][0]
    assert "oauth_provider" not in data["items"][0]


async def test_list_discover_paginates_results(discover_session: AsyncSession):
    current_user = await _create_user(discover_session, "page-current", "Current")
    first_candidate = await _create_user(discover_session, "page-first", "First")
    second_candidate = await _create_user(discover_session, "page-second", "Second")
    third_candidate = await _create_user(discover_session, "page-third", "Third")

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(discover_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.get("/api/discover?page=2&limit=1")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 2
    assert data["limit"] == 1
    assert data["total"] == 3
    assert data["has_more"] is True
    assert [item["id"] for item in data["items"]] == [second_candidate.id]
    assert first_candidate.id != second_candidate.id != third_candidate.id


async def test_list_discover_filters_by_species_city_age_relationship_and_nsfw(
    discover_session: AsyncSession,
):
    current_user = await _create_user(discover_session, "filter-current", "Current")
    current_user.nsfw_enabled = True
    await discover_session.commit()

    matching_user = await _create_user(discover_session, "filter-match", "Match")
    matching_user.age = 29
    matching_user.city = "Portland"
    matching_user.relationship_style = "Monogamous"

    wrong_species = await _create_user(discover_session, "filter-species", "Wrong Species")
    wrong_species.city = "Portland"

    wrong_city = await _create_user(discover_session, "filter-city", "Wrong City")
    wrong_city.city = "Seattle"

    wrong_age = await _create_user(discover_session, "filter-age", "Wrong Age")
    wrong_age.age = 40
    wrong_age.city = "Portland"

    wrong_relationship = await _create_user(
        discover_session, "filter-relationship", "Wrong Relationship"
    )
    wrong_relationship.city = "Portland"
    wrong_relationship.relationship_style = "polyamorous"

    nsfw_user = await _create_user(discover_session, "filter-nsfw", "NSFW")
    nsfw_user.age = 28
    nsfw_user.city = "Portland"
    nsfw_user.relationship_style = "monogamous"

    await discover_session.commit()

    await _create_fursona(
        discover_session,
        user_id=matching_user.id,
        name="River",
        species="Fox",
    )
    await _create_fursona(
        discover_session,
        user_id=wrong_species.id,
        name="Blaze",
        species="Wolf",
    )
    await _create_fursona(
        discover_session,
        user_id=wrong_city.id,
        name="Glint",
        species="Fox",
    )
    await _create_fursona(
        discover_session,
        user_id=wrong_age.id,
        name="Moss",
        species="Fox",
    )
    await _create_fursona(
        discover_session,
        user_id=wrong_relationship.id,
        name="Dune",
        species="Fox",
    )
    await _create_fursona(
        discover_session,
        user_id=nsfw_user.id,
        name="Ember",
        species="Fox",
        is_nsfw=True,
    )

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(discover_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            safe_response = c.get(
                "/api/discover?species=fox&city=port&min_age=26&max_age=32"
                "&relationship_style=monogamous&include_nsfw=false"
            )
            nsfw_response = c.get(
                "/api/discover?species=fox&city=port&min_age=26&max_age=32"
                "&relationship_style=monogamous&include_nsfw=true"
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert safe_response.status_code == 200
    assert [item["id"] for item in safe_response.json()["items"]] == [matching_user.id]

    assert nsfw_response.status_code == 200
    assert [item["id"] for item in nsfw_response.json()["items"]] == [nsfw_user.id, matching_user.id]


async def test_list_discover_filters_by_multiple_species(discover_session: AsyncSession):
    current_user = await _create_user(discover_session, "multi-species-current", "Current")
    fox_user = await _create_user(discover_session, "multi-species-fox", "Fox Match")
    wolf_user = await _create_user(discover_session, "multi-species-wolf", "Wolf Match")
    cat_user = await _create_user(discover_session, "multi-species-cat", "Cat Miss")

    await _create_fursona(
        discover_session,
        user_id=fox_user.id,
        name="Cinder",
        species="Fox",
    )
    await _create_fursona(
        discover_session,
        user_id=wolf_user.id,
        name="Nova",
        species="Wolf",
    )
    await _create_fursona(
        discover_session,
        user_id=cat_user.id,
        name="Miso",
        species="Cat",
    )

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(discover_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.get("/api/discover?species=fox,wolf")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [wolf_user.id, fox_user.id]


async def test_list_discover_hides_nsfw_candidates_when_current_user_has_nsfw_disabled(
    discover_session: AsyncSession,
):
    current_user = await _create_user(discover_session, "safe-current", "Current")
    current_user.nsfw_enabled = False
    candidate = await _create_user(discover_session, "safe-candidate", "Candidate")
    await discover_session.commit()

    await _create_fursona(
        discover_session,
        user_id=candidate.id,
        name="Night",
        species="Fox",
        is_nsfw=True,
    )

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(discover_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.get("/api/discover?include_nsfw=true")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    assert response.json()["items"] == []


async def test_list_discover_keeps_candidate_with_safe_primary_visible_when_secondary_is_nsfw(
    discover_session: AsyncSession,
):
    current_user = await _create_user(discover_session, "mixed-current", "Current")
    current_user.nsfw_enabled = False
    candidate = await _create_user(discover_session, "mixed-candidate", "Candidate")
    await discover_session.commit()

    await _create_fursona(
        discover_session,
        user_id=candidate.id,
        name="Daylight",
        species="Fox",
        is_primary=True,
        is_nsfw=False,
    )
    await _create_fursona(
        discover_session,
        user_id=candidate.id,
        name="Midnight",
        species="Fox",
        is_primary=False,
        is_nsfw=True,
    )

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    app.dependency_overrides[get_db] = _override_db(discover_session)
    try:
        with TestClient(app, follow_redirects=False) as c:
            response = c.get("/api/discover?include_nsfw=true")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [candidate.id]


def test_list_discover_rejects_invalid_age_range(client: TestClient):
    current_user = User(
        id=1,
        oauth_provider="google",
        oauth_id="invalid-age-current",
        email="current@example.com",
        display_name="Current",
    )

    app.dependency_overrides[get_current_user] = _override_current_user(current_user)
    try:
        response = client.get("/api/discover?min_age=40&max_age=20")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 422
    assert response.json()["detail"] == "min_age must be less than or equal to max_age"
