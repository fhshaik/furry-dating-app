"""Tests for the PackJoinRequestVote ORM model."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.pack import Pack
from app.models.pack_join_request import PackJoinRequest
from app.models.pack_join_request_vote import (
    PackJoinRequestVote,
    PackJoinRequestVoteDecision,
)
from app.models.user import User


@pytest.fixture()
async def sqlite_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


def test_pack_join_request_vote_tablename():
    assert PackJoinRequestVote.__tablename__ == "pack_join_request_votes"


def test_pack_join_request_vote_has_required_columns():
    column_names = set(PackJoinRequestVote.__table__.c.keys())
    assert column_names == {"join_request_id", "voter_user_id", "decision", "created_at"}


async def test_create_pack_join_request_vote(sqlite_session: AsyncSession):
    creator = User(
        oauth_provider="google",
        oauth_id="vote-creator",
        display_name="Creator",
    )
    requester = User(
        oauth_provider="google",
        oauth_id="vote-requester",
        display_name="Requester",
    )
    voter = User(
        oauth_provider="google",
        oauth_id="vote-voter",
        display_name="Voter",
    )
    sqlite_session.add_all([creator, requester, voter])
    await sqlite_session.commit()

    pack = Pack(creator_id=creator.id, name="North Pack", consensus_required=True)
    sqlite_session.add(pack)
    await sqlite_session.commit()

    join_request = PackJoinRequest(pack_id=pack.id, user_id=requester.id)
    sqlite_session.add(join_request)
    await sqlite_session.commit()

    vote = PackJoinRequestVote(
        join_request_id=join_request.id,
        voter_user_id=voter.id,
        decision=PackJoinRequestVoteDecision.APPROVED,
    )
    sqlite_session.add(vote)
    await sqlite_session.commit()
    await sqlite_session.refresh(vote)

    assert vote.join_request_id == join_request.id
    assert vote.voter_user_id == voter.id
    assert vote.decision == PackJoinRequestVoteDecision.APPROVED
    assert vote.created_at is not None
