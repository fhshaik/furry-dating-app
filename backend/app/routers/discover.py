from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.models.fursona import Fursona
from app.models.match import Match
from app.models.swipe import Swipe
from app.models.user import User
from app.schemas.discover import DiscoverResponse

router = APIRouter(prefix="/api/discover", tags=["discover"])


@router.get("", response_model=DiscoverResponse)
async def list_discover_candidates(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    species: list[str] | None = Query(default=None),
    city: str | None = Query(default=None),
    min_age: int | None = Query(default=None, ge=18),
    max_age: int | None = Query(default=None, ge=18),
    relationship_style: str | None = Query(default=None),
    include_nsfw: bool | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DiscoverResponse:
    if min_age is not None and max_age is not None and min_age > max_age:
        raise HTTPException(status_code=422, detail="min_age must be less than or equal to max_age")

    seen_user_ids = select(Swipe.target_user_id).where(
        Swipe.swiper_id == current_user.id,
        Swipe.target_user_id.is_not(None),
    )
    matched_user_ids = (
        select(Match.user_b_id.label("candidate_id"))
        .where(
            Match.user_a_id == current_user.id,
            Match.unmatched_at.is_(None),
        )
        .union(
            select(Match.user_a_id.label("candidate_id")).where(
                Match.user_b_id == current_user.id,
                Match.unmatched_at.is_(None),
            )
        )
        .subquery()
    )

    filters: list[object] = [
        User.id != current_user.id,
        User.id.not_in(select(matched_user_ids.c.candidate_id)),
        User.id.not_in(seen_user_ids),
    ]

    normalized_species = sorted(
        {
            value.strip().lower()
            for item in species or []
            for value in item.split(",")
            if value.strip()
        }
    )
    if normalized_species:
        filters.append(
            exists(
                select(Fursona.id).where(
                    Fursona.user_id == User.id,
                    func.lower(Fursona.species).in_(normalized_species),
                )
            )
        )

    normalized_city = city.strip().lower() if city and city.strip() else None
    if normalized_city:
        filters.append(func.lower(User.city).like(f"%{normalized_city}%"))

    if min_age is not None:
        filters.append(User.age.is_not(None))
        filters.append(User.age >= min_age)

    if max_age is not None:
        filters.append(User.age.is_not(None))
        filters.append(User.age <= max_age)

    normalized_relationship_style = (
        relationship_style.strip().lower()
        if relationship_style and relationship_style.strip()
        else None
    )
    if normalized_relationship_style:
        filters.append(func.lower(User.relationship_style) == normalized_relationship_style)

    should_include_nsfw = current_user.nsfw_enabled and include_nsfw is not False
    if not should_include_nsfw:
        filters.append(
            ~exists(
                select(Fursona.id).where(
                    Fursona.user_id == User.id,
                    Fursona.is_primary.is_(True),
                    Fursona.is_nsfw.is_(True),
                )
            )
        )

    offset = (page - 1) * limit

    total = await db.scalar(select(func.count()).select_from(User).where(*filters))
    result = await db.execute(
        select(User)
        .where(*filters)
        .order_by(User.created_at.desc(), User.id.desc())
        .offset(offset)
        .limit(limit)
    )
    items = list(result.scalars().all())
    return DiscoverResponse(
        items=items,
        page=page,
        limit=limit,
        total=total or 0,
        has_more=(offset + len(items)) < (total or 0),
    )
