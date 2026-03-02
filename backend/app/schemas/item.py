from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.validation import TrimmedNonEmptyLimitedStr, TrimmedOptionalStr


class ItemCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: TrimmedNonEmptyLimitedStr(255)
    description: TrimmedOptionalStr() = None


class ItemUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: TrimmedNonEmptyLimitedStr(255) | None = Field(default=None)
    description: TrimmedOptionalStr() = None


class ItemResponse(BaseModel):
    id: int
    name: str
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
