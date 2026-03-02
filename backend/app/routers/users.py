"""User profile endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserMeResponse, UserPublicResponse, UserUpdateRequest

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/{user_id}", response_model=UserPublicResponse)
async def get_user_profile(
    user_id: int,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Return a user's public profile by ID."""
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/me", response_model=UserMeResponse)
async def update_me(
    payload: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Update the currently authenticated user's profile fields."""
    update_data = payload.model_dump(exclude_unset=True)

    if "display_name" in update_data and update_data["display_name"] is None:
        raise HTTPException(status_code=422, detail="display_name cannot be null")

    for field, value in update_data.items():
        setattr(current_user, field, value)

    if update_data:
        await db.commit()
        await db.refresh(current_user)

    return current_user


@router.delete("/me", status_code=204)
async def delete_me(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Permanently delete the currently authenticated user's account."""
    await db.delete(current_user)
    await db.commit()
    response.delete_cookie("access_token")
