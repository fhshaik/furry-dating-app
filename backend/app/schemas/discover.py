from pydantic import BaseModel, Field

from app.schemas.user import UserPublicResponse


class DiscoverResponse(BaseModel):
    items: list[UserPublicResponse]
    page: int = Field(ge=1)
    limit: int = Field(ge=1)
    total: int = Field(ge=0)
    has_more: bool
