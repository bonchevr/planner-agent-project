"""add share_token to gameplanrecord

Revision ID: 002sharetok
Revises: 001initial
Create Date: 2026-03-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002sharetok"
down_revision: Union[str, None] = "001initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "gameplanrecord",
        sa.Column("share_token", sa.String(), nullable=True),
    )
    # UNIQUE but nullable — PostgreSQL allows multiple NULLs in a unique index.
    op.create_index(
        "ix_gameplanrecord_share_token",
        "gameplanrecord",
        ["share_token"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_gameplanrecord_share_token", table_name="gameplanrecord")
    op.drop_column("gameplanrecord", "share_token")
