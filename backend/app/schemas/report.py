from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from app.schemas.validation import TrimmedNonEmptyLimitedStr, TrimmedOptionalLimitedStr

ReportContentType = Literal["fursona", "message", "pack"]


class UserReportCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    reported_user_id: int
    reason: TrimmedNonEmptyLimitedStr(100)
    details: TrimmedOptionalLimitedStr(1000) = None


class ContentReportCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    content_type: ReportContentType
    content_id: int
    reason: TrimmedNonEmptyLimitedStr(100)
    details: TrimmedOptionalLimitedStr(1000) = None


class ReportResponse(BaseModel):
    id: int
    reporter_id: int
    reported_user_id: int | None
    content_type: ReportContentType | None
    content_id: int | None
    reason: str
    details: str | None
    created_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def validate_target_shape(self) -> "ReportResponse":
        has_user_target = self.reported_user_id is not None
        has_content_target = self.content_type is not None and self.content_id is not None
        if has_user_target == has_content_target:
            raise ValueError("Report must target either a user or a content item")
        return self
