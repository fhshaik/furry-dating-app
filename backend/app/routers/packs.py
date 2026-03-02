from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import String, cast, delete, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.models.conversation import Conversation, ConversationType
from app.models.conversation_member import ConversationMember
from app.models.pack import Pack
from app.models.pack_join_request import PackJoinRequest, PackJoinRequestStatus
from app.models.pack_join_request_vote import PackJoinRequestVote, PackJoinRequestVoteDecision
from app.models.pack_member import PackMember, PackMemberRole
from app.models.user import User
from app.schemas.pack import (
    PackCreate,
    PackDetailMemberResponse,
    PackDetailResponse,
    PackJoinRequestDecision,
    PackJoinRequestDetailResponse,
    PackJoinRequestResponse,
    PackJoinRequestUserResponse,
    PackJoinRequestVoteResponse,
    PackListResponse,
    PackMemberUserResponse,
    PackMineItemResponse,
    PackMineListResponse,
    PackResponse,
    PackUpdate,
)
from app.services.notifications import (
    PackJoinRequestNotifier,
    get_pack_join_request_notifier,
)

router = APIRouter(prefix="/api/packs", tags=["packs"])


async def _build_join_request_votes(
    db: AsyncSession,
    join_request_ids: list[int],
) -> dict[int, list[PackJoinRequestVoteResponse]]:
    if not join_request_ids:
        return {}

    vote_rows = await db.execute(
        select(PackJoinRequestVote, User)
        .join(User, User.id == PackJoinRequestVote.voter_user_id)
        .where(PackJoinRequestVote.join_request_id.in_(join_request_ids))
        .order_by(
            PackJoinRequestVote.join_request_id.asc(),
            PackJoinRequestVote.created_at.asc(),
            PackJoinRequestVote.voter_user_id.asc(),
        )
    )

    votes_by_request: dict[int, list[PackJoinRequestVoteResponse]] = {
        join_request_id: [] for join_request_id in join_request_ids
    }
    for vote, user in vote_rows.all():
        votes_by_request.setdefault(vote.join_request_id, []).append(
            PackJoinRequestVoteResponse(
                voter_user_id=vote.voter_user_id,
                decision=vote.decision,
                created_at=vote.created_at,
                user=PackJoinRequestUserResponse(
                    id=user.id,
                    display_name=user.display_name,
                ),
            )
        )

    return votes_by_request


async def _count_required_approvals(
    db: AsyncSession,
    pack_id: int,
) -> int:
    count = await db.scalar(
        select(func.count())
        .select_from(PackMember)
        .where(PackMember.pack_id == pack_id)
    )
    return count or 0


def _can_manage_join_requests(pack: Pack, membership: PackMember | None) -> bool:
    if membership is None:
        return False
    if pack.consensus_required:
        return True
    return membership.role == PackMemberRole.ADMIN


async def _serialize_join_request_response(
    db: AsyncSession,
    pack: Pack,
    join_request: PackJoinRequest,
    approvals_required: int | None = None,
) -> PackJoinRequestResponse:
    if approvals_required is None:
        approvals_required = await _count_required_approvals(db, pack.id)
    votes_by_request = await _build_join_request_votes(db, [join_request.id])
    votes = votes_by_request.get(join_request.id, [])

    return PackJoinRequestResponse(
        id=join_request.id,
        pack_id=join_request.pack_id,
        user_id=join_request.user_id,
        status=join_request.status,
        created_at=join_request.created_at,
        votes=votes,
        approvals_required=approvals_required,
        approvals_received=sum(
            1 for vote in votes if vote.decision == PackJoinRequestVoteDecision.APPROVED
        ),
    )


@router.get("", response_model=PackListResponse)
async def list_packs(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    species: list[str] | None = Query(default=None),
    search: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PackListResponse:
    normalized_species = sorted(
        {
            value.strip().lower()
            for item in species or []
            for value in item.split(",")
            if value.strip()
        }
    )
    normalized_search = search.strip().lower() if search and search.strip() else None

    filters: list[object] = [
        Pack.is_open.is_(True),
        ~exists(
            select(PackMember.pack_id).where(
                PackMember.pack_id == Pack.id,
                PackMember.user_id == current_user.id,
            )
        ),
    ]

    if normalized_species:
        species_json = func.lower(cast(Pack.species_tags, String))
        filters.append(
            or_(*[species_json.like(f'%"{species_value}"%') for species_value in normalized_species])
        )

    if normalized_search:
        filters.append(
            or_(
                func.lower(Pack.name).like(f"%{normalized_search}%"),
                func.lower(func.coalesce(Pack.description, "")).like(f"%{normalized_search}%"),
            )
        )

    offset = (page - 1) * limit

    total = await db.scalar(select(func.count()).select_from(Pack).where(*filters))
    result = await db.execute(
        select(Pack)
        .where(*filters)
        .order_by(Pack.created_at.desc(), Pack.id.desc())
        .offset(offset)
        .limit(limit)
    )
    items = list(result.scalars().all())

    return PackListResponse(
        items=items,
        page=page,
        limit=limit,
        total=total or 0,
        has_more=(offset + len(items)) < (total or 0),
    )


@router.get("/mine", response_model=PackMineListResponse)
async def list_my_packs(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PackMineListResponse:
    offset = (page - 1) * limit

    member_count_subquery = (
        select(func.count())
        .select_from(PackMember)
        .where(PackMember.pack_id == Pack.id)
        .correlate(Pack)
        .scalar_subquery()
    )

    filters = [
        exists(
            select(PackMember.pack_id).where(
                PackMember.pack_id == Pack.id,
                PackMember.user_id == current_user.id,
            )
        ),
    ]

    total = await db.scalar(select(func.count()).select_from(Pack).where(*filters))
    result = await db.execute(
        select(Pack, member_count_subquery.label("member_count"))
        .where(*filters)
        .order_by(Pack.created_at.desc(), Pack.id.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = result.all()
    pack_ids = [pack.id for pack, _ in rows]

    pack_conv = (
        await db.execute(
            select(Conversation.pack_id, Conversation.id).where(
                Conversation.type == ConversationType.PACK,
                Conversation.pack_id.in_(pack_ids),
            )
        )
    )
    pack_id_to_conv = {row[0]: row[1] for row in pack_conv.all()}

    items = [
        PackMineItemResponse(
            id=pack.id,
            creator_id=pack.creator_id,
            name=pack.name,
            description=pack.description,
            image_url=pack.image_url,
            species_tags=pack.species_tags,
            max_size=pack.max_size,
            consensus_required=pack.consensus_required,
            is_open=pack.is_open,
            created_at=pack.created_at,
            member_count=member_count,
            conversation_id=pack_id_to_conv.get(pack.id),
        )
        for pack, member_count in rows
    ]

    return PackMineListResponse(
        items=items,
        page=page,
        limit=limit,
        total=total or 0,
        has_more=(offset + len(items)) < (total or 0),
    )


@router.get("/{pack_id}", response_model=PackDetailResponse)
async def get_pack(
    pack_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PackDetailResponse:
    pack = await db.get(Pack, pack_id)
    if pack is None:
        raise HTTPException(status_code=404, detail="Pack not found")

    membership = await db.scalar(
        select(PackMember).where(
            PackMember.pack_id == pack_id,
            PackMember.user_id == current_user.id,
        )
    )
    if not pack.is_open and membership is None:
        raise HTTPException(status_code=404, detail="Pack not found")

    member_rows = await db.execute(
        select(PackMember, User)
        .join(User, User.id == PackMember.user_id)
        .where(PackMember.pack_id == pack_id)
        .order_by(
            PackMember.role.asc(),
            PackMember.joined_at.asc(),
            PackMember.user_id.asc(),
        )
    )
    pack_conv = await db.scalar(
        select(Conversation).where(
            Conversation.pack_id == pack_id,
            Conversation.type == ConversationType.PACK,
        )
    )
    conversation_id = pack_conv.id if (pack_conv is not None and membership is not None) else None

    return PackDetailResponse(
        id=pack.id,
        creator_id=pack.creator_id,
        name=pack.name,
        description=pack.description,
        image_url=pack.image_url,
        species_tags=pack.species_tags,
        max_size=pack.max_size,
        consensus_required=pack.consensus_required,
        is_open=pack.is_open,
        created_at=pack.created_at,
        members=[
            PackDetailMemberResponse(
                user=PackMemberUserResponse(
                    id=user.id,
                    display_name=user.display_name,
                ),
                role=member.role,
                joined_at=member.joined_at,
            )
            for member, user in member_rows.all()
        ],
        conversation_id=conversation_id,
    )


@router.post("", response_model=PackResponse, status_code=status.HTTP_201_CREATED)
async def create_pack(
    payload: PackCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Pack:
    pack = Pack(
        creator_id=current_user.id,
        name=payload.name,
        description=payload.description,
        image_url=payload.image_url,
        species_tags=payload.species_tags,
        max_size=payload.max_size,
        consensus_required=payload.consensus_required,
        is_open=payload.is_open,
    )
    db.add(pack)
    await db.flush()

    conversation = Conversation(type=ConversationType.PACK, pack_id=pack.id)
    db.add(conversation)
    await db.flush()

    db.add(ConversationMember(conversation_id=conversation.id, user_id=current_user.id))
    db.add(
        PackMember(
            pack_id=pack.id,
            user_id=current_user.id,
            role=PackMemberRole.ADMIN,
        )
    )

    await db.commit()
    await db.refresh(pack)
    return pack


@router.patch("/{pack_id}", response_model=PackResponse)
async def update_pack(
    pack_id: int,
    payload: PackUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Pack:
    pack = await db.get(Pack, pack_id)
    if pack is None:
        raise HTTPException(status_code=404, detail="Pack not found")

    membership = await db.scalar(
        select(PackMember).where(
            PackMember.pack_id == pack_id,
            PackMember.user_id == current_user.id,
        )
    )
    if membership is None or membership.role != PackMemberRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to update this pack")

    update_data = payload.model_dump(exclude_unset=True)
    if "name" in update_data and update_data["name"] is None:
        raise HTTPException(status_code=422, detail="name cannot be null")
    if "max_size" in update_data and update_data["max_size"] is not None:
        member_count = await _count_required_approvals(db, pack.id)
        if update_data["max_size"] < member_count:
            raise HTTPException(
                status_code=400,
                detail="max_size cannot be less than current member count",
            )

    for field, value in update_data.items():
        setattr(pack, field, value)

    if update_data:
        await db.commit()
        await db.refresh(pack)

    return pack


@router.delete("/{pack_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pack(
    pack_id: int,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    pack = await db.get(Pack, pack_id)
    if pack is None:
        raise HTTPException(status_code=404, detail="Pack not found")

    membership = await db.scalar(
        select(PackMember).where(
            PackMember.pack_id == pack_id,
            PackMember.user_id == current_user.id,
        )
    )
    if membership is None or membership.role != PackMemberRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to delete this pack")

    await db.execute(delete(PackJoinRequest).where(PackJoinRequest.pack_id == pack_id))
    await db.execute(delete(PackMember).where(PackMember.pack_id == pack_id))
    await db.delete(pack)
    await db.commit()
    response.status_code = status.HTTP_204_NO_CONTENT


@router.delete("/{pack_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pack_member(
    pack_id: int,
    user_id: int,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    pack = await db.get(Pack, pack_id)
    if pack is None:
        raise HTTPException(status_code=404, detail="Pack not found")

    membership = await db.scalar(
        select(PackMember).where(
            PackMember.pack_id == pack_id,
            PackMember.user_id == current_user.id,
        )
    )
    if current_user.id != user_id and (
        membership is None or membership.role != PackMemberRole.ADMIN
    ):
        raise HTTPException(status_code=403, detail="Not authorized to remove this member")

    target_membership = await db.scalar(
        select(PackMember).where(
            PackMember.pack_id == pack_id,
            PackMember.user_id == user_id,
        )
    )
    if target_membership is None:
        raise HTTPException(status_code=404, detail="Member not found")

    if target_membership.role == PackMemberRole.ADMIN:
        admin_count = await db.scalar(
            select(func.count())
            .select_from(PackMember)
            .where(
                PackMember.pack_id == pack_id,
                PackMember.role == PackMemberRole.ADMIN,
            )
        )
        if (admin_count or 0) <= 1:
            raise HTTPException(status_code=400, detail="Cannot remove the last admin")

    pending_request_ids = select(PackJoinRequest.id).where(
        PackJoinRequest.pack_id == pack_id,
        PackJoinRequest.status == PackJoinRequestStatus.PENDING,
    )
    await db.execute(
        delete(PackJoinRequestVote).where(
            PackJoinRequestVote.voter_user_id == user_id,
            PackJoinRequestVote.join_request_id.in_(pending_request_ids),
        )
    )
    await db.delete(target_membership)
    await db.commit()
    response.status_code = status.HTTP_204_NO_CONTENT


@router.post(
    "/{pack_id}/join-request",
    response_model=PackJoinRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_pack_join_request(
    pack_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    join_request_notifier: PackJoinRequestNotifier = Depends(get_pack_join_request_notifier),
) -> PackJoinRequest:
    pack = await db.get(Pack, pack_id)
    if pack is None:
        raise HTTPException(status_code=404, detail="Pack not found")

    if not pack.is_open:
        raise HTTPException(status_code=403, detail="Pack is not open to join requests")

    membership = await db.scalar(
        select(PackMember).where(
            PackMember.pack_id == pack_id,
            PackMember.user_id == current_user.id,
        )
    )
    if membership is not None:
        raise HTTPException(status_code=400, detail="Already a member of this pack")

    existing_request = await db.scalar(
        select(PackJoinRequest).where(
            PackJoinRequest.pack_id == pack_id,
            PackJoinRequest.user_id == current_user.id,
            PackJoinRequest.status == PackJoinRequestStatus.PENDING,
        )
    )
    if existing_request is not None:
        raise HTTPException(status_code=409, detail="Join request already pending")

    join_request = PackJoinRequest(
        pack_id=pack_id,
        user_id=current_user.id,
        status=PackJoinRequestStatus.PENDING,
    )
    db.add(join_request)
    await db.commit()
    await db.refresh(join_request)

    recipient_filters = [
        PackMember.pack_id == pack_id,
        PackMember.user_id != current_user.id,
    ]
    if not pack.consensus_required:
        recipient_filters.append(PackMember.role == PackMemberRole.ADMIN)

    recipient_rows = await db.execute(select(PackMember.user_id).where(*recipient_filters))
    await join_request_notifier.notify_pack_join_request_received(
        join_request,
        [user_id for (user_id,) in recipient_rows.all()],
    )
    return await _serialize_join_request_response(db, pack, join_request)


@router.get("/{pack_id}/join-requests", response_model=list[PackJoinRequestDetailResponse])
async def list_pack_join_requests(
    pack_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PackJoinRequestDetailResponse]:
    pack = await db.get(Pack, pack_id)
    if pack is None:
        raise HTTPException(status_code=404, detail="Pack not found")

    membership = await db.scalar(
        select(PackMember).where(
            PackMember.pack_id == pack_id,
            PackMember.user_id == current_user.id,
        )
    )
    if not _can_manage_join_requests(pack, membership):
        raise HTTPException(status_code=403, detail="Not authorized to view join requests")

    request_rows = await db.execute(
        select(PackJoinRequest, User)
        .join(User, User.id == PackJoinRequest.user_id)
        .where(
            PackJoinRequest.pack_id == pack_id,
            PackJoinRequest.status == PackJoinRequestStatus.PENDING,
        )
        .order_by(PackJoinRequest.created_at.asc(), PackJoinRequest.id.asc())
    )

    join_requests_with_users = request_rows.all()
    approvals_required = await _count_required_approvals(db, pack.id)
    votes_by_request = await _build_join_request_votes(
        db,
        [join_request.id for join_request, _ in join_requests_with_users],
    )

    return [
        PackJoinRequestDetailResponse(
            id=join_request.id,
            pack_id=join_request.pack_id,
            user_id=join_request.user_id,
            status=join_request.status,
            created_at=join_request.created_at,
            user=PackJoinRequestUserResponse(
                id=user.id,
                display_name=user.display_name,
            ),
            votes=votes_by_request.get(join_request.id, []),
            approvals_required=approvals_required,
            approvals_received=sum(
                1
                for vote in votes_by_request.get(join_request.id, [])
                if vote.decision == PackJoinRequestVoteDecision.APPROVED
            ),
        )
        for join_request, user in join_requests_with_users
    ]


@router.patch(
    "/{pack_id}/join-requests/{user_id}",
    response_model=PackJoinRequestResponse,
)
async def decide_pack_join_request(
    pack_id: int,
    user_id: int,
    payload: PackJoinRequestDecision,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PackJoinRequestResponse:
    pack = await db.get(Pack, pack_id)
    if pack is None:
        raise HTTPException(status_code=404, detail="Pack not found")

    membership = await db.scalar(
        select(PackMember).where(
            PackMember.pack_id == pack_id,
            PackMember.user_id == current_user.id,
        )
    )
    if not _can_manage_join_requests(pack, membership):
        raise HTTPException(status_code=403, detail="Not authorized to manage join requests")

    join_request = await db.scalar(
        select(PackJoinRequest).where(
            PackJoinRequest.pack_id == pack_id,
            PackJoinRequest.user_id == user_id,
            PackJoinRequest.status == PackJoinRequestStatus.PENDING,
        )
    )
    if join_request is None:
        raise HTTPException(status_code=404, detail="Join request not found")

    if payload.status == PackJoinRequestStatus.APPROVED.value:
        member_count = await _count_required_approvals(db, pack.id)
        if member_count >= pack.max_size:
            raise HTTPException(status_code=409, detail="Pack is already full")

    decision = PackJoinRequestVoteDecision(payload.status)
    vote = await db.get(
        PackJoinRequestVote,
        {
            "join_request_id": join_request.id,
            "voter_user_id": current_user.id,
        },
    )
    if vote is None:
        vote = PackJoinRequestVote(
            join_request_id=join_request.id,
            voter_user_id=current_user.id,
            decision=decision,
        )
        db.add(vote)
    else:
        vote.decision = decision

    approvals_required = await _count_required_approvals(db, pack.id)

    if decision == PackJoinRequestVoteDecision.DENIED:
        join_request.status = PackJoinRequestStatus.DENIED
    elif not pack.consensus_required:
        join_request.status = PackJoinRequestStatus.APPROVED
    else:
        approved_vote_count = await db.scalar(
            select(func.count())
            .select_from(PackJoinRequestVote)
            .where(
                PackJoinRequestVote.join_request_id == join_request.id,
                PackJoinRequestVote.decision == PackJoinRequestVoteDecision.APPROVED,
            )
        )
        join_request.status = (
            PackJoinRequestStatus.APPROVED
            if (approved_vote_count or 0) >= approvals_required
            else PackJoinRequestStatus.PENDING
        )

    if join_request.status == PackJoinRequestStatus.APPROVED:
        member_count = await _count_required_approvals(db, pack.id)
        if member_count >= pack.max_size:
            await db.rollback()
            raise HTTPException(status_code=409, detail="Pack is already full")

        existing_member = await db.scalar(
            select(PackMember).where(
                PackMember.pack_id == pack_id,
                PackMember.user_id == user_id,
            )
        )
        if existing_member is not None:
            raise HTTPException(status_code=400, detail="User is already a member of this pack")

        db.add(
            PackMember(
                pack_id=pack_id,
                user_id=user_id,
                role=PackMemberRole.MEMBER,
            )
        )
        pack_conv = await db.scalar(
            select(Conversation).where(
                Conversation.pack_id == pack_id,
                Conversation.type == ConversationType.PACK,
            )
        )
        if pack_conv is not None:
            db.add(ConversationMember(conversation_id=pack_conv.id, user_id=user_id))

    await db.commit()
    await db.refresh(join_request)
    return await _serialize_join_request_response(
        db,
        pack,
        join_request,
        approvals_required=approvals_required,
    )
