"""initial schema

Revision ID: 001initial
Revises:
Create Date: 2026-03-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=40), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_username", "user", ["username"], unique=True)

    op.create_table(
        "gameplanrecord",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("project_name", sa.String(), nullable=False),
        sa.Column("problem_statement", sa.String(), nullable=False),
        sa.Column("core_features", sa.String(), nullable=False),
        sa.Column("target_platform", sa.String(), nullable=False),
        sa.Column("preferred_language", sa.String(), nullable=False),
        sa.Column("team_size", sa.String(), nullable=False),
        sa.Column("timeline", sa.String(), nullable=False),
        sa.Column("constraints", sa.String(), nullable=False),
        sa.Column("gameplan_md", sa.String(), nullable=False),
        sa.Column("stack_json", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_gameplanrecord_slug", "gameplanrecord", ["slug"], unique=False)
    op.create_index(
        "ix_gameplanrecord_user_id", "gameplanrecord", ["user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_gameplanrecord_user_id", table_name="gameplanrecord")
    op.drop_index("ix_gameplanrecord_slug", table_name="gameplanrecord")
    op.drop_table("gameplanrecord")
    op.drop_index("ix_user_username", table_name="user")
    op.drop_table("user")
