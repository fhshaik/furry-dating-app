from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PackMemberRole(str, Enum):
    ADMIN = "admin"
    MEMBER = "member"


class PackMember(Base):
    __tablename__ = "pack_members"

    pack_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("packs.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[PackMemberRole] = mapped_column(
        SqlEnum(
            PackMemberRole,
            name="pack_member_role",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        server_default=PackMemberRole.MEMBER.value,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
