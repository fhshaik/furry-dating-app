from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.models.conversation import Conversation, ConversationType
from app.models.conversation_member import ConversationMember
from app.models.message import Message
from app.models.user import User
from app.schemas.conversation import ConversationResponse, MessageResponse

router = APIRouter(prefix="/api/conversations", tags=["conversations"])

_MAX_LIMIT = 50


@router.get("/by-pack/{pack_id}", response_model=ConversationResponse)
async def get_conversation_by_pack(
    pack_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    """Return the pack's conversation if the current user is a member."""
    conv = await db.scalar(
        select(Conversation)
        .join(ConversationMember, ConversationMember.conversation_id == Conversation.id)
        .where(
            Conversation.pack_id == pack_id,
            Conversation.type == ConversationType.PACK,
            ConversationMember.user_id == current_user.id,
        )
    )
    if conv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pack conversation not found or you are not a member",
        )
    unread = await db.scalar(
        select(func.count(Message.id)).where(
            Message.conversation_id == conv.id,
            Message.sender_id != current_user.id,
            Message.is_read == False,  # noqa: E712
        )
    )
    return ConversationResponse.model_validate(
        {
            "id": conv.id,
            "type": conv.type,
            "pack_id": conv.pack_id,
            "created_at": conv.created_at,
            "unread_count": unread or 0,
        }
    )


@router.get("/direct-with/{user_id}", response_model=ConversationResponse)
async def get_direct_conversation_with(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    """Return the direct conversation between current user and the given user, if it exists."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot get direct conversation with yourself",
        )
    # Find DIRECT conversation where both are members (exactly two members)
    subq = (
        select(ConversationMember.conversation_id)
        .where(ConversationMember.user_id.in_([current_user.id, user_id]))
        .group_by(ConversationMember.conversation_id)
        .having(func.count(ConversationMember.user_id) == 2)
    )
    conv = await db.scalar(
        select(Conversation)
        .where(
            Conversation.id.in_(subq),
            Conversation.type == ConversationType.DIRECT,
        )
    )
    if conv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No direct conversation with this user",
        )
    unread = await db.scalar(
        select(func.count(Message.id)).where(
            Message.conversation_id == conv.id,
            Message.sender_id != current_user.id,
            Message.is_read == False,  # noqa: E712
        )
    )
    return ConversationResponse.model_validate(
        {
            "id": conv.id,
            "type": conv.type,
            "pack_id": conv.pack_id,
            "created_at": conv.created_at,
            "unread_count": unread or 0,
        }
    )


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ConversationResponse]:
    unread_count_subquery = (
        select(
            Message.conversation_id.label("conversation_id"),
            func.count(Message.id).label("unread_count"),
        )
        .where(
            Message.sender_id != current_user.id,
            Message.is_read == False,  # noqa: E712
        )
        .group_by(Message.conversation_id)
        .subquery()
    )

    result = await db.execute(
        select(Conversation, func.coalesce(unread_count_subquery.c.unread_count, 0))
        .join(ConversationMember, ConversationMember.conversation_id == Conversation.id)
        .outerjoin(
            unread_count_subquery,
            unread_count_subquery.c.conversation_id == Conversation.id,
        )
        .where(ConversationMember.user_id == current_user.id)
        .order_by(Conversation.created_at.desc(), Conversation.id.desc())
    )
    return [
        ConversationResponse.model_validate(
            {
                "id": conv.id,
                "type": conv.type,
                "pack_id": conv.pack_id,
                "created_at": conv.created_at,
                "unread_count": unread_count,
            }
        )
        for conv, unread_count in result.all()
    ]


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    conversation_id: int,
    before_id: int | None = Query(default=None),
    limit: int = Query(default=_MAX_LIMIT, ge=1, le=_MAX_LIMIT),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MessageResponse]:
    conversation = await db.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    member = await db.scalar(
        select(ConversationMember).where(
            ConversationMember.conversation_id == conversation_id,
            ConversationMember.user_id == current_user.id,
        )
    )
    if member is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this conversation")

    query = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.sent_at.desc(), Message.id.desc())
        .limit(limit)
    )
    if before_id is not None:
        pivot = await db.get(Message, before_id)
        if pivot is not None:
            query = query.where(
                (Message.sent_at < pivot.sent_at)
                | ((Message.sent_at == pivot.sent_at) & (Message.id < pivot.id))
            )

    result = await db.execute(query)
    return [MessageResponse.model_validate(msg) for msg in result.scalars().all()]
