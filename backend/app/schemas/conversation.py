from datetime import datetime

from pydantic import BaseModel, ConfigDict
from app.schemas.validation import TrimmedNonEmptyStr

from app.models.conversation import ConversationType


class ChatMessageCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    content: TrimmedNonEmptyStr


class ConversationResponse(BaseModel):
    id: int
    type: ConversationType
    pack_id: int | None
    created_at: datetime
    unread_count: int

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    sender_id: int
    content: str
    sent_at: datetime
    is_read: bool

    model_config = {"from_attributes": True}
