"""add email to user

Revision ID: 003useremail
Revises: 002sharetok
Create Date: 2026-03-09

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003useremail"
down_revision: Union[str, None] = "002sharetok"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column("email", sa.String(), nullable=True),
    )
    # UNIQUE but nullable — PostgreSQL allows multiple NULLs in a unique index.
    op.create_index("ix_user_email", "user", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_user_email", table_name="user")
    op.drop_column("user", "email")
