"""Create the separate labor rate catalog and dated prices.

Revision ID: 20260901_0007
Revises: 20260831_0006
Create Date: 2026-09-01
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260901_0007"
down_revision: str | None = "20260831_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "labor_rates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rate_name", sa.String(length=200), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_labor_rates")),
        sa.UniqueConstraint("rate_name", name="uq_labor_rates_rate_name"),
    )
    op.create_index(
        op.f("ix_labor_rates_is_active"),
        "labor_rates",
        ["is_active"],
        unique=False,
    )

    op.create_table(
        "labor_rate_prices",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "labor_rate_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "rate_per_hour",
            sa.Numeric(precision=18, scale=6),
            nullable=False,
        ),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "rate_per_hour >= 0",
            name=op.f("ck_labor_rate_prices_rate_nonnegative"),
        ),
        sa.ForeignKeyConstraint(
            ["labor_rate_id"],
            ["labor_rates.id"],
            name=op.f("fk_labor_rate_prices_labor_rate_id_labor_rates"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_labor_rate_prices")),
    )
    op.create_index(
        op.f("ix_labor_rate_prices_effective_date"),
        "labor_rate_prices",
        ["effective_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_labor_rate_prices_labor_rate_id"),
        "labor_rate_prices",
        ["labor_rate_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_labor_rate_prices_labor_rate_id"),
        table_name="labor_rate_prices",
    )
    op.drop_index(
        op.f("ix_labor_rate_prices_effective_date"),
        table_name="labor_rate_prices",
    )
    op.drop_table("labor_rate_prices")
    op.drop_index(
        op.f("ix_labor_rates_is_active"),
        table_name="labor_rates",
    )
    op.drop_table("labor_rates")
