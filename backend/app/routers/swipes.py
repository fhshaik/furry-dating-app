from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.models.conversation import Conversation, ConversationType
from app.models.conversation_member import ConversationMember
from app.models.match import Match
from app.models.pack import Pack
from app.models.swipe import Swipe, SwipeAction
from app.models.user import User
from app.schemas.swipe import SwipeCreateRequest, SwipeResponse
from app.services.notifications import MatchNotifier, get_match_notifier

router = APIRouter(prefix="/api/swipes", tags=["swipes"])


@router.post("", response_model=SwipeResponse, status_code=status.HTTP_201_CREATED)
async def create_swipe(
    payload: SwipeCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    match_notifier: MatchNotifier = Depends(get_match_notifier),
) -> SwipeResponse:
    if payload.target_user_id is not None:
        if payload.target_user_id == current_user.id:
            raise HTTPException(status_code=400, detail="Cannot swipe on yourself")

        target_user = await db.get(User, payload.target_user_id)
        if target_user is None:
            raise HTTPException(status_code=404, detail="Target user not found")
    else:
        target_pack = await db.get(Pack, payload.target_pack_id)
        if target_pack is None:
            raise HTTPException(status_code=404, detail="Target pack not found")

    swipe = Swipe(
        swiper_id=current_user.id,
        target_user_id=payload.target_user_id,
        target_pack_id=payload.target_pack_id,
        action=payload.action,
    )
    db.add(swipe)

    is_match = False
    new_match: Match | None = None
    if payload.target_user_id is not None and payload.action == SwipeAction.LIKE:
        active_match = await db.scalar(
            select(Match).where(
                Match.unmatched_at.is_(None),
                or_(
                    and_(
                        Match.user_a_id == current_user.id,
                        Match.user_b_id == payload.target_user_id,
                    ),
                    and_(
                        Match.user_a_id == payload.target_user_id,
                        Match.user_b_id == current_user.id,
                    ),
                ),
            )
        )
        if active_match is None:
            reciprocal_like = await db.scalar(
                select(Swipe).where(
                    Swipe.swiper_id == payload.target_user_id,
                    Swipe.target_user_id == current_user.id,
                    Swipe.action == SwipeAction.LIKE,
                )
            )
            if reciprocal_like is not None:
                new_match = Match(
                    user_a_id=current_user.id,
                    user_b_id=payload.target_user_id,
                )
                db.add(new_match)
                await db.flush()

                conversation = Conversation(type=ConversationType.DIRECT)
                db.add(conversation)
                await db.flush()
                db.add(ConversationMember(conversation_id=conversation.id, user_id=current_user.id))
                db.add(ConversationMember(conversation_id=conversation.id, user_id=payload.target_user_id))

                is_match = True

    await db.commit()
    await db.refresh(swipe)
    if new_match is not None:
        await match_notifier.notify_match_created(new_match)

    return SwipeResponse(
        id=swipe.id,
        swiper_id=swipe.swiper_id,
        target_user_id=swipe.target_user_id,
        target_pack_id=swipe.target_pack_id,
        action=swipe.action,
        created_at=swipe.created_at,
        is_match=is_match,
    )
