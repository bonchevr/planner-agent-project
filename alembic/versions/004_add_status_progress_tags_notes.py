"""add status, progress, tags, notes to gameplanrecord

Revision ID: 004statusetc
Revises: 003useremail
Create Date: 2026-03-11

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004statusetc"
down_revision: Union[str, None] = "003useremail"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "gameplanrecord",
        sa.Column("status", sa.String(), nullable=False, server_default="planning"),
    )
    op.add_column(
        "gameplanrecord",
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "gameplanrecord",
        sa.Column("tags", sa.String(), nullable=False, server_default=""),
    )
    op.add_column(
        "gameplanrecord",
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
    )
    op.create_index("ix_gameplanrecord_status", "gameplanrecord", ["status"])


def downgrade() -> None:
    op.drop_index("ix_gameplanrecord_status", table_name="gameplanrecord")
    op.drop_column("gameplanrecord", "notes")
    op.drop_column("gameplanrecord", "tags")
    op.drop_column("gameplanrecord", "progress")
    op.drop_column("gameplanrecord", "status")
