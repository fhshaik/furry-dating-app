"""Seed example data (users, fursonas, packs, messages, etc.)

Revision ID: 0008
Revises: 0007
Create Date: 2026-03-01 00:00:00.000000

Only runs when the database has no users (fresh install / local dev).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table(name: str, *columns: sa.Column) -> sa.Table:
    return sa.table(name, *columns)


def upgrade() -> None:
    conn = op.get_bind()
    # Only seed when database has no users (fresh start)
    user_count = conn.execute(sa.text("SELECT COUNT(*) FROM users")).scalar()
    if user_count and user_count > 0:
        return

    users = _table(
        "users",
        sa.column("id", sa.Integer()),
        sa.column("oauth_provider", sa.String(32)),
        sa.column("oauth_id", sa.String(255)),
        sa.column("email", sa.String(255)),
        sa.column("display_name", sa.String(100)),
        sa.column("bio", sa.Text()),
        sa.column("age", sa.Integer()),
        sa.column("city", sa.String(100)),
        sa.column("nsfw_enabled", sa.Boolean()),
        sa.column("relationship_style", sa.String(50)),
        sa.column("created_at", sa.DateTime()),
    )
    example_users = [
        (1, "google", "seed-wolf-1", "luna.wolf@example.com", "Luna", "Wolf from the north. Love hiking and art.", 28, "Denver", False, "monogamous", None),
        (2, "google", "seed-fox-2", "ember.fox@example.com", "Ember", "Fox artist and coffee enthusiast.", 25, "Portland", False, "polyamorous", None),
        (3, "discord", "seed-dragon-3", "blaze.dragon@example.com", "Blaze", "Dragon who likes games and comics.", 30, "Seattle", False, "monogamous", None),
        (4, "google", "seed-bunny-4", "cotton.bunny@example.com", "Cotton", "Bunny fursuiter and con-goer.", 22, "Austin", False, "open", None),
        (5, "discord", "seed-tiger-5", "stripe.tiger@example.com", "Stripe", "Tiger musician. Bass and synths.", 27, "Chicago", False, "monogamous", None),
    ]
    for row in example_users:
        conn.execute(
            sa.insert(users).values(
                id=row[0],
                oauth_provider=row[1],
                oauth_id=row[2],
                email=row[3],
                display_name=row[4],
                bio=row[5],
                age=row[6],
                city=row[7],
                nsfw_enabled=row[8],
                relationship_style=row[9],
                created_at=sa.func.now(),
            )
        )

    fursonas = _table(
        "fursonas",
        sa.column("id", sa.Integer()),
        sa.column("user_id", sa.Integer()),
        sa.column("name", sa.String(100)),
        sa.column("species", sa.String(100)),
        sa.column("traits", sa.JSON()),
        sa.column("description", sa.Text()),
        sa.column("image_url", sa.String(500)),
        sa.column("is_primary", sa.Boolean()),
        sa.column("is_nsfw", sa.Boolean()),
        sa.column("created_at", sa.DateTime()),
    )
    example_fursonas = [
        (1, 1, "Luna", "Wolf", None, "Grey wolf with blue eyes.", None, True, False),
        (2, 2, "Ember", "Fox", None, "Red fox, orange and white.", None, True, False),
        (3, 3, "Blaze", "Dragon", None, "Fire dragon, scales and wings.", None, True, False),
        (4, 4, "Cotton", "Bunny", None, "Fluffy white bunny.", None, True, False),
        (5, 5, "Stripe", "Tiger", None, "Orange tiger with black stripes.", None, True, False),
    ]
    for row in example_fursonas:
        conn.execute(
            sa.insert(fursonas).values(
                id=row[0],
                user_id=row[1],
                name=row[2],
                species=row[3],
                traits=row[4],
                description=row[5],
                image_url=row[6],
                is_primary=row[7],
                is_nsfw=row[8],
                created_at=sa.func.now(),
            )
        )

    packs_t = _table(
        "packs",
        sa.column("id", sa.Integer()),
        sa.column("creator_id", sa.Integer()),
        sa.column("name", sa.String(100)),
        sa.column("description", sa.Text()),
        sa.column("image_url", sa.String(500)),
        sa.column("species_tags", sa.JSON()),
        sa.column("max_size", sa.Integer()),
        sa.column("consensus_required", sa.Boolean()),
        sa.column("is_open", sa.Boolean()),
        sa.column("created_at", sa.DateTime()),
    )
    example_packs = [
        (1, 1, "Mountain Howlers", "Wolf pack from the Rockies. Hikes and campfires.", None, ["wolf"], 10, False, True),
        (2, 2, "Fox Den Artists", "Art and fursuiting crew. Con meetups.", None, ["fox"], 8, True, True),
        (3, 3, "Dragon's Hoard", "Gaming and comics. All dragons welcome.", None, ["dragon"], 12, False, True),
    ]
    for row in example_packs:
        conn.execute(
            sa.insert(packs_t).values(
                id=row[0],
                creator_id=row[1],
                name=row[2],
                description=row[3],
                image_url=row[4],
                species_tags=row[5],
                max_size=row[6],
                consensus_required=row[7],
                is_open=row[8],
                created_at=sa.func.now(),
            )
        )

    pack_members_t = _table(
        "pack_members",
        sa.column("pack_id", sa.Integer()),
        sa.column("user_id", sa.Integer()),
        sa.column("role", sa.String(20)),
        sa.column("joined_at", sa.DateTime()),
    )
    for pack_id, user_id, role in [
        (1, 1, "admin"), (1, 2, "member"), (1, 3, "member"),
        (2, 2, "admin"), (2, 1, "member"), (2, 4, "member"),
        (3, 3, "admin"), (3, 4, "member"), (3, 5, "member"),
    ]:
        conn.execute(
            sa.insert(pack_members_t).values(
                pack_id=pack_id,
                user_id=user_id,
                role=role,
                joined_at=sa.func.now(),
            )
        )

    matches_t = _table(
        "matches",
        sa.column("id", sa.Integer()),
        sa.column("user_a_id", sa.Integer()),
        sa.column("user_b_id", sa.Integer()),
        sa.column("created_at", sa.DateTime()),
        sa.column("unmatched_at", sa.DateTime()),
    )
    for mid, ua, ub in [(1, 1, 2), (2, 1, 3), (3, 2, 4), (4, 3, 5)]:
        conn.execute(
            sa.insert(matches_t).values(
                id=mid,
                user_a_id=ua,
                user_b_id=ub,
                created_at=sa.func.now(),
                unmatched_at=None,
            )
        )

    conv_t = _table(
        "conversations",
        sa.column("id", sa.Integer()),
        sa.column("type", sa.String(20)),
        sa.column("pack_id", sa.Integer()),
        sa.column("created_at", sa.DateTime()),
    )
    # Direct convs: 1-2, 1-3, 2-4. Pack conv: pack 1
    for cid, ctype, pack_id in [
        (1, "direct", None),
        (2, "direct", None),
        (3, "direct", None),
        (4, "pack", 1),
    ]:
        conn.execute(
            sa.insert(conv_t).values(
                id=cid,
                type=ctype,
                pack_id=pack_id,
                created_at=sa.func.now(),
            )
        )

    conv_members_t = _table(
        "conversation_members",
        sa.column("conversation_id", sa.Integer()),
        sa.column("user_id", sa.Integer()),
    )
    for cid, uid in [
        (1, 1), (1, 2),
        (2, 1), (2, 3),
        (3, 2), (3, 4),
        (4, 1), (4, 2), (4, 3),
    ]:
        conn.execute(
            sa.insert(conv_members_t).values(conversation_id=cid, user_id=uid)
        )

    messages_t = _table(
        "messages",
        sa.column("id", sa.Integer()),
        sa.column("conversation_id", sa.Integer()),
        sa.column("sender_id", sa.Integer()),
        sa.column("content", sa.Text()),
        sa.column("sent_at", sa.DateTime()),
        sa.column("is_read", sa.Boolean()),
    )
    example_messages = [
        (1, 1, 1, "Hey Ember! Loved your latest art piece.", sa.func.now(), False),
        (2, 1, 2, "Thanks Luna! Want to grab coffee sometime?", sa.func.now(), False),
        (3, 1, 1, "Yes! How about Saturday?", sa.func.now(), False),
        (4, 2, 1, "Blaze, that game night was awesome.", sa.func.now(), False),
        (5, 2, 3, "We should do it again. Next week?", sa.func.now(), False),
        (6, 3, 2, "Cotton, are you going to AnthroCon?", sa.func.now(), False),
        (7, 3, 4, "Yes! I'll be in fursuit. Look for the white bunny!", sa.func.now(), False),
        (8, 4, 1, "Pack hike this weekend? Same trail as last time.", sa.func.now(), False),
        (9, 4, 2, "I'm in!", sa.func.now(), False),
        (10, 4, 3, "Count me in too.", sa.func.now(), False),
    ]
    for row in example_messages:
        conn.execute(
            sa.insert(messages_t).values(
                id=row[0],
                conversation_id=row[1],
                sender_id=row[2],
                content=row[3],
                sent_at=row[4],
                is_read=row[5],
            )
        )

    swipes_t = _table(
        "swipes",
        sa.column("id", sa.Integer()),
        sa.column("swiper_id", sa.Integer()),
        sa.column("target_user_id", sa.Integer()),
        sa.column("target_pack_id", sa.Integer()),
        sa.column("action", sa.String(20)),
        sa.column("created_at", sa.DateTime()),
    )
    for sid, swiper, target_user, target_pack, action in [
        (1, 1, 2, None, "like"),
        (2, 1, 4, None, "like"),
        (3, 2, 1, None, "like"),
        (4, 2, 3, None, "pass"),
        (5, 3, 5, None, "like"),
    ]:
        conn.execute(
            sa.insert(swipes_t).values(
                id=sid,
                swiper_id=swiper,
                target_user_id=target_user,
                target_pack_id=target_pack,
                action=action,
                created_at=sa.func.now(),
            )
        )

    notifications_t = _table(
        "notifications",
        sa.column("id", sa.Integer()),
        sa.column("user_id", sa.Integer()),
        sa.column("type", sa.String(50)),
        sa.column("payload", sa.JSON()),
        sa.column("is_read", sa.Boolean()),
        sa.column("created_at", sa.DateTime()),
    )
    conn.execute(
        sa.insert(notifications_t).values(
            user_id=1,
            type="new_match",
            payload={"match_id": 1, "other_user_id": 2},
            is_read=False,
            created_at=sa.func.now(),
        )
    )
    conn.execute(
        sa.insert(notifications_t).values(
            user_id=2,
            type="new_message",
            payload={"conversation_id": 1, "sender_id": 1},
            is_read=False,
            created_at=sa.func.now(),
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    # Remove seed data by explicit IDs (seed users 1–5, packs 1–3, convs 1–4)
    conn.execute(sa.text("DELETE FROM notifications WHERE user_id IN (1, 2, 3, 4, 5)"))
    conn.execute(sa.text("DELETE FROM messages WHERE sender_id IN (1, 2, 3, 4, 5)"))
    conn.execute(sa.text("DELETE FROM conversation_members WHERE conversation_id IN (1, 2, 3, 4)"))
    conn.execute(sa.text("DELETE FROM conversations WHERE id IN (1, 2, 3, 4)"))
    conn.execute(sa.text("DELETE FROM matches WHERE user_a_id IN (1, 2, 3, 4, 5) OR user_b_id IN (1, 2, 3, 4, 5)"))
    conn.execute(sa.text("DELETE FROM pack_members WHERE pack_id IN (1, 2, 3)"))
    conn.execute(sa.text("DELETE FROM swipes WHERE swiper_id IN (1, 2, 3, 4, 5)"))
    conn.execute(sa.text("DELETE FROM packs WHERE id IN (1, 2, 3)"))
    conn.execute(sa.text("DELETE FROM fursonas WHERE user_id IN (1, 2, 3, 4, 5)"))
    conn.execute(sa.text("DELETE FROM users WHERE oauth_id LIKE 'seed-%'"))
