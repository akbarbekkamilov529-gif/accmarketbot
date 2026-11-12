"""add user preferred language

Revision ID: 7c1f2a9b4d6e
Revises: 936dceed4bd0
Create Date: 2026-11-12 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "7c1f2a9b4d6e"
down_revision: Union[str, None] = "936dceed4bd0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("preferred_language", sa.String(length=8), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("preferred_language")
