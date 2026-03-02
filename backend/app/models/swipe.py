from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.pack import Pack  # noqa: F401


class SwipeAction(str, Enum):
    LIKE = "like"
    PASS = "pass"


class Swipe(Base):
    __tablename__ = "swipes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    swiper_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    target_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    target_pack_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("packs.id", ondelete="CASCADE"), nullable=True
    )
    action: Mapped[SwipeAction] = mapped_column(
        SqlEnum(
            SwipeAction,
            name="swipe_action",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
