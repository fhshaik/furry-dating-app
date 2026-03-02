from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import case, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.models.conversation import Conversation, ConversationType
from app.models.conversation_member import ConversationMember
from app.models.match import Match
from app.models.user import User
from app.schemas.match import MatchResponse
from app.schemas.user import UserPublicResponse

router = APIRouter(prefix="/api/matches", tags=["matches"])


@router.get("", response_model=list[MatchResponse])
async def list_matches(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MatchResponse]:
    matched_user_id = case(
        (Match.user_a_id == current_user.id, Match.user_b_id),
        else_=Match.user_a_id,
    )
    result = await db.execute(
        select(Match, User)
        .join(User, User.id == matched_user_id)
        .where(
            Match.unmatched_at.is_(None),
            or_(
                Match.user_a_id == current_user.id,
                Match.user_b_id == current_user.id,
            ),
        )
        .order_by(Match.created_at.desc(), Match.id.desc())
    )
    rows = result.all()

    my_conv_ids = select(ConversationMember.conversation_id).where(
        ConversationMember.user_id == current_user.id,
    )
    other_member_rows = await db.execute(
        select(Conversation.id, ConversationMember.user_id)
        .select_from(Conversation)
        .join(ConversationMember, ConversationMember.conversation_id == Conversation.id)
        .where(
            Conversation.type == ConversationType.DIRECT,
            Conversation.id.in_(my_conv_ids),
            ConversationMember.user_id != current_user.id,
        )
    )
    other_user_to_conv = {row[1]: row[0] for row in other_member_rows.all()}

    return [
        MatchResponse(
            id=match.id,
            created_at=match.created_at,
            matched_user=UserPublicResponse.model_validate(matched_user),
            last_message_preview=None,
            conversation_id=other_user_to_conv.get(matched_user.id),
        )
        for match, matched_user in rows
    ]


@router.delete("/{match_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_match(
    match_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    match = await db.scalar(
        select(Match).where(
            Match.id == match_id,
            Match.unmatched_at.is_(None),
        )
    )
    if match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")

    if current_user.id not in {match.user_a_id, match.user_b_id}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to unmatch this user",
        )

    match.unmatched_at = datetime.now(UTC).replace(tzinfo=None)
    await db.commit()
