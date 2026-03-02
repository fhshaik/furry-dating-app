"""Seed species tags

Revision ID: 0003
Revises: 0002
Create Date: 2026-02-28 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SPECIES = [
    ("Axolotl", "axolotl"),
    ("Bear", "bear"),
    ("Bird", "bird"),
    ("Bunny", "bunny"),
    ("Cat", "cat"),
    ("Cheetah", "cheetah"),
    ("Deer", "deer"),
    ("Dog", "dog"),
    ("Dragon", "dragon"),
    ("Duck", "duck"),
    ("Ferret", "ferret"),
    ("Fish", "fish"),
    ("Fox", "fox"),
    ("Frog", "frog"),
    ("Griffin", "griffin"),
    ("Horse", "horse"),
    ("Hyena", "hyena"),
    ("Jackal", "jackal"),
    ("Kangaroo", "kangaroo"),
    ("Kirin", "kirin"),
    ("Leopard", "leopard"),
    ("Lion", "lion"),
    ("Lizard", "lizard"),
    ("Mink", "mink"),
    ("Mongoose", "mongoose"),
    ("Mouse", "mouse"),
    ("Otter", "otter"),
    ("Panther", "panther"),
    ("Phoenix", "phoenix"),
    ("Pony", "pony"),
    ("Rabbit", "rabbit"),
    ("Raccoon", "raccoon"),
    ("Rat", "rat"),
    ("Sergal", "sergal"),
    ("Shark", "shark"),
    ("Skunk", "skunk"),
    ("Snake", "snake"),
    ("Snow Leopard", "snow-leopard"),
    ("Sphinx", "sphinx"),
    ("Squirrel", "squirrel"),
    ("Tiger", "tiger"),
    ("Unicorn", "unicorn"),
    ("Wolf", "wolf"),
    ("Wyvern", "wyvern"),
    ("Other", "other"),
]

species_tags = sa.table(
    "species_tags",
    sa.column("name", sa.String(length=100)),
    sa.column("slug", sa.String(length=100)),
)


def upgrade() -> None:
    conn = op.get_bind()
    for name, slug in SPECIES:
        existing = conn.execute(
            sa.select(sa.literal(1))
            .select_from(species_tags)
            .where(species_tags.c.slug == slug)
            .limit(1)
        ).scalar()
        if existing is None:
            conn.execute(sa.insert(species_tags).values(name=name, slug=slug))


def downgrade() -> None:
    conn = op.get_bind()
    for _, slug in SPECIES:
        conn.execute(sa.delete(species_tags).where(species_tags.c.slug == slug))
