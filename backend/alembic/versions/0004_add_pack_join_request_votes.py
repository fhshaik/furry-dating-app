"""Add pack join request votes

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-01 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pack_join_request_votes",
        sa.Column("join_request_id", sa.Integer(), nullable=False),
        sa.Column("voter_user_id", sa.Integer(), nullable=False),
        sa.Column(
            "decision",
            sa.Enum(
                "approved",
                "denied",
                name="join_request_vote_decision",
            ),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["join_request_id"],
            ["pack_join_requests.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["voter_user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("join_request_id", "voter_user_id"),
    )


def downgrade() -> None:
    op.drop_table("pack_join_request_votes")
