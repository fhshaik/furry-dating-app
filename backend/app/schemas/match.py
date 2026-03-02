from datetime import datetime

from pydantic import BaseModel

from app.schemas.user import UserPublicResponse


class MatchResponse(BaseModel):
    id: int
    created_at: datetime
    matched_user: UserPublicResponse
    last_message_preview: str | None = None
    conversation_id: int | None = None
