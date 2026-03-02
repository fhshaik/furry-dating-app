from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PackJoinRequestVoteDecision(str, Enum):
    APPROVED = "approved"
    DENIED = "denied"


class PackJoinRequestVote(Base):
    __tablename__ = "pack_join_request_votes"

    join_request_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("pack_join_requests.id", ondelete="CASCADE"),
        primary_key=True,
    )
    voter_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    decision: Mapped[PackJoinRequestVoteDecision] = mapped_column(
        SqlEnum(
            PackJoinRequestVoteDecision,
            name="join_request_vote_decision",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
