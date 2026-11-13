"""add hourly platform split

Revision ID: b2e7f4a9c1d8
Revises: 7c1f2a9b4d6e
Create Date: 2026-11-13 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "b2e7f4a9c1d8"
down_revision: Union[str, None] = "7c1f2a9b4d6e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "platform_balances",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "available",
            sa.Numeric(precision=14, scale=2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "total_earned",
            sa.Numeric(precision=14, scale=2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_platform_balances")),
    )
    op.execute(
        "INSERT INTO platform_balances (id, available, total_earned) VALUES (1, 0, 0)"
    )

    with op.batch_alter_table("hourly_releases", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "seller_amount",
                sa.Numeric(precision=14, scale=2),
                server_default=sa.text("0"),
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "platform_amount",
                sa.Numeric(precision=14, scale=2),
                server_default=sa.text("0"),
                nullable=False,
            )
        )

    op.execute(
        "UPDATE orders SET commission_amount = 0, seller_amount = amount "
        "WHERE status = 'pending_payment'"
    )


def downgrade() -> None:
    with op.batch_alter_table("hourly_releases", schema=None) as batch_op:
        batch_op.drop_column("platform_amount")
        batch_op.drop_column("seller_amount")

    op.drop_table("platform_balances")
