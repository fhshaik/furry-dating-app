from datetime import datetime

from pydantic import BaseModel, model_validator

from app.models.swipe import SwipeAction


class SwipeCreateRequest(BaseModel):
    action: SwipeAction
    target_user_id: int | None = None
    target_pack_id: int | None = None

    @model_validator(mode="after")
    def validate_single_target(self) -> "SwipeCreateRequest":
        if (self.target_user_id is None) == (self.target_pack_id is None):
            raise ValueError("Exactly one of target_user_id or target_pack_id must be provided")
        return self


class SwipeResponse(BaseModel):
    id: int
    swiper_id: int
    target_user_id: int | None
    target_pack_id: int | None
    action: SwipeAction
    created_at: datetime
    is_match: bool

    model_config = {"from_attributes": True}
