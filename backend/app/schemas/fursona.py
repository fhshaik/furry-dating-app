from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.schemas.validation import (
    TrimmedNonEmptyLimitedStr,
    TrimmedOptionalLimitedStr,
    TrimmedOptionalStr,
)


class FursonaCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: TrimmedNonEmptyLimitedStr(100)
    species: TrimmedNonEmptyLimitedStr(100)
    traits: Any | None = None
    description: TrimmedOptionalStr() = None
    image_url: TrimmedOptionalLimitedStr(500) = None
    is_primary: bool = False
    is_nsfw: bool = False


class FursonaUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: TrimmedNonEmptyLimitedStr(100) | None = None
    species: TrimmedNonEmptyLimitedStr(100) | None = None
    traits: Any | None = None
    description: TrimmedOptionalStr() = None
    image_url: TrimmedOptionalLimitedStr(500) = None
    is_primary: bool | None = None
    is_nsfw: bool | None = None


class FursonaResponse(BaseModel):
    id: int
    user_id: int
    name: str
    species: str
    traits: Any | None
    description: str | None
    image_url: str | None
    is_primary: bool
    is_nsfw: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UploadUrlResponse(BaseModel):
    upload_url: str
    key: str
    public_url: str
