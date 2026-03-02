"""Fursona endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.models.fursona import Fursona
from app.models.user import User
from app.schemas.fursona import FursonaCreate, FursonaResponse, FursonaUpdate, UploadUrlResponse
from app.services.s3 import ALLOWED_IMAGE_CONTENT_TYPES, generate_upload_url

router = APIRouter(prefix="/api/fursonas", tags=["fursonas"])

MAX_FURSONAS = 5


@router.get("", response_model=list[FursonaResponse])
async def list_fursonas(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Fursona]:
    """List all fursonas belonging to the authenticated user."""
    result = await db.execute(
        select(Fursona).where(Fursona.user_id == current_user.id)
    )
    return list(result.scalars().all())


@router.post("", response_model=FursonaResponse, status_code=201)
async def create_fursona(
    payload: FursonaCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Fursona:
    """Create a new fursona for the authenticated user (max 5)."""
    count_result = await db.execute(
        select(func.count()).select_from(Fursona).where(Fursona.user_id == current_user.id)
    )
    count = count_result.scalar_one()
    if count >= MAX_FURSONAS:
        raise HTTPException(status_code=422, detail="Maximum of 5 fursonas allowed per user")

    fursona = Fursona(
        user_id=current_user.id,
        name=payload.name,
        species=payload.species,
        traits=payload.traits,
        description=payload.description,
        image_url=payload.image_url,
        is_primary=payload.is_primary,
        is_nsfw=payload.is_nsfw,
    )
    db.add(fursona)
    await db.commit()
    await db.refresh(fursona)
    return fursona


@router.delete("/{fursona_id}", status_code=204)
async def delete_fursona(
    fursona_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a fursona (owner only)."""
    result = await db.execute(select(Fursona).where(Fursona.id == fursona_id))
    fursona = result.scalar_one_or_none()
    if fursona is None:
        raise HTTPException(status_code=404, detail="Fursona not found")
    if fursona.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this fursona")

    await db.delete(fursona)
    await db.commit()


@router.post("/{fursona_id}/primary", response_model=FursonaResponse)
async def set_primary_fursona(
    fursona_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Fursona:
    """Set a fursona as the primary fursona for the authenticated user (owner only)."""
    result = await db.execute(select(Fursona).where(Fursona.id == fursona_id))
    fursona = result.scalar_one_or_none()
    if fursona is None:
        raise HTTPException(status_code=404, detail="Fursona not found")
    if fursona.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this fursona")

    await db.execute(
        update(Fursona).where(Fursona.user_id == current_user.id).values(is_primary=False)
    )
    fursona.is_primary = True

    await db.commit()
    await db.refresh(fursona)
    return fursona


@router.get("/{fursona_id}/upload-url", response_model=UploadUrlResponse)
async def get_fursona_upload_url(
    fursona_id: int,
    content_type: str = Query(default="image/jpeg"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UploadUrlResponse:
    """Generate a presigned S3 PUT URL for uploading a fursona image (owner only)."""
    result = await db.execute(select(Fursona).where(Fursona.id == fursona_id))
    fursona = result.scalar_one_or_none()
    if fursona is None:
        raise HTTPException(status_code=404, detail="Fursona not found")
    if fursona.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to upload for this fursona")

    if content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"content_type must be one of: {', '.join(sorted(ALLOWED_IMAGE_CONTENT_TYPES))}",
        )

    upload_url, key, public_url = generate_upload_url(fursona_id, content_type)
    return UploadUrlResponse(upload_url=upload_url, key=key, public_url=public_url)


@router.patch("/{fursona_id}", response_model=FursonaResponse)
async def update_fursona(
    fursona_id: int,
    payload: FursonaUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Fursona:
    """Update a fursona (owner only)."""
    result = await db.execute(select(Fursona).where(Fursona.id == fursona_id))
    fursona = result.scalar_one_or_none()
    if fursona is None:
        raise HTTPException(status_code=404, detail="Fursona not found")
    if fursona.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this fursona")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(fursona, field, value)

    await db.commit()
    await db.refresh(fursona)
    return fursona
