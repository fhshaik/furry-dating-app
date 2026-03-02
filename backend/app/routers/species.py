"""Species tag endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.species_tag import SpeciesTag
from app.schemas.species import SpeciesTagResponse

router = APIRouter(prefix="/api/species", tags=["species"])


@router.get("", response_model=list[SpeciesTagResponse])
async def list_species(
    db: AsyncSession = Depends(get_db),
) -> list[SpeciesTag]:
    """Return all species tags ordered alphabetically by name."""
    result = await db.execute(select(SpeciesTag).order_by(SpeciesTag.name))
    return list(result.scalars().all())
