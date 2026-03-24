"""add is_admin and is_active to user

Revision ID: 005useradmin
Revises: 004statusetc
Create Date: 2026-03-24

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005useradmin"
down_revision: Union[str, None] = "004statusetc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
    )
    op.add_column(
        "user",
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("user", "is_admin")
    op.drop_column("user", "is_active")
