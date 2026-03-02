from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.pack_join_request import PackJoinRequestStatus
from app.models.pack_join_request_vote import PackJoinRequestVoteDecision
from app.models.pack_member import PackMemberRole
from app.schemas.validation import (
    TrimmedNonEmptyLimitedStr,
    TrimmedOptionalLimitedStr,
    TrimmedOptionalStr,
    TrimmedStringList,
)


class PackCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: TrimmedNonEmptyLimitedStr(100)
    description: TrimmedOptionalStr() = None
    image_url: TrimmedOptionalLimitedStr(500) = None
    species_tags: TrimmedStringList(100) | None = None
    max_size: int = Field(default=10, ge=1)
    consensus_required: bool = False
    is_open: bool = True


class PackUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: TrimmedNonEmptyLimitedStr(100) | None = None
    description: TrimmedOptionalStr() = None
    image_url: TrimmedOptionalLimitedStr(500) = None
    species_tags: TrimmedStringList(100) | None = None
    max_size: int | None = Field(default=None, ge=1)
    consensus_required: bool | None = None
    is_open: bool | None = None


class PackResponse(BaseModel):
    id: int
    creator_id: int
    name: str
    description: str | None
    image_url: str | None
    species_tags: list[str] | None
    max_size: int
    consensus_required: bool
    is_open: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PackListResponse(BaseModel):
    items: list[PackResponse]
    page: int = Field(ge=1)
    limit: int = Field(ge=1)
    total: int = Field(ge=0)
    has_more: bool


class PackMineItemResponse(PackResponse):
    member_count: int
    conversation_id: int | None = None


class PackMineListResponse(BaseModel):
    items: list[PackMineItemResponse]
    page: int = Field(ge=1)
    limit: int = Field(ge=1)
    total: int = Field(ge=0)
    has_more: bool


class PackMemberUserResponse(BaseModel):
    id: int
    display_name: str


class PackDetailMemberResponse(BaseModel):
    user: PackMemberUserResponse
    role: PackMemberRole
    joined_at: datetime


class PackDetailResponse(PackResponse):
    members: list[PackDetailMemberResponse]
    conversation_id: int | None = None


class PackJoinRequestUserResponse(BaseModel):
    id: int
    display_name: str


class PackJoinRequestVoteResponse(BaseModel):
    voter_user_id: int
    decision: PackJoinRequestVoteDecision
    created_at: datetime
    user: PackJoinRequestUserResponse


class PackJoinRequestResponse(BaseModel):
    id: int
    pack_id: int
    user_id: int
    status: PackJoinRequestStatus
    created_at: datetime
    votes: list[PackJoinRequestVoteResponse] = Field(default_factory=list)
    approvals_required: int = Field(ge=0)
    approvals_received: int = Field(ge=0)

    model_config = {"from_attributes": True}


class PackJoinRequestDetailResponse(BaseModel):
    id: int
    pack_id: int
    user_id: int
    status: PackJoinRequestStatus
    created_at: datetime
    user: PackJoinRequestUserResponse
    votes: list[PackJoinRequestVoteResponse] = Field(default_factory=list)
    approvals_required: int = Field(ge=0)
    approvals_received: int = Field(ge=0)


class PackJoinRequestDecision(BaseModel):
    status: Literal[
        PackJoinRequestStatus.APPROVED.value,
        PackJoinRequestStatus.DENIED.value,
    ]
