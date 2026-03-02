from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.schemas.validation import TrimmedNonEmptyLimitedStr, TrimmedOptionalLimitedStr, TrimmedOptionalStr


class UserUpdateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    display_name: TrimmedNonEmptyLimitedStr(100) | None = None
    bio: TrimmedOptionalStr() = None
    age: int | None = None
    city: TrimmedOptionalLimitedStr(100) = None
    nsfw_enabled: bool | None = None
    relationship_style: TrimmedOptionalLimitedStr(50) = None

    @field_validator("display_name")
    @classmethod
    def display_name_not_empty(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("display_name must not be empty")
        return v


class UserPublicResponse(BaseModel):
    id: int
    display_name: str
    bio: str | None
    age: int | None
    city: str | None
    relationship_style: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserMeResponse(BaseModel):
    id: int
    oauth_provider: str
    email: str | None
    display_name: str
    bio: str | None
    age: int | None
    city: str | None
    nsfw_enabled: bool
    relationship_style: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
