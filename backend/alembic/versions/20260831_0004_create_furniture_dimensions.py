"""Create canonical furniture dimensions.

Revision ID: 20260831_0004
Revises: 20260831_0003
Create Date: 2026-08-31
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260831_0004"
down_revision: str | None = "20260831_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "furniture_dimensions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("furniture_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("width_mm", sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column("height_mm", sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column("depth_mm", sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column("unit", sa.String(length=4), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column(
            "is_locked",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
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
            "(is_locked = false AND locked_at IS NULL) OR "
            "(is_locked = true AND locked_at IS NOT NULL)",
            name=op.f("ck_furniture_dimensions_lock_state_consistent"),
        ),
        sa.CheckConstraint(
            "source IN ('manual', 'ai_estimate')",
            name=op.f("ck_furniture_dimensions_source_allowed"),
        ),
        sa.CheckConstraint(
            "unit IN ('mm', 'cm', 'm', 'in')",
            name=op.f("ck_furniture_dimensions_unit_allowed"),
        ),
        sa.CheckConstraint(
            "width_mm > 0 AND height_mm > 0 AND depth_mm > 0",
            name=op.f("ck_furniture_dimensions_values_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["furniture_id"],
            ["furniture.id"],
            name=op.f("fk_furniture_dimensions_furniture_id_furniture"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_furniture_dimensions")),
        sa.UniqueConstraint(
            "furniture_id",
            name="uq_furniture_dimensions_furniture_id",
        ),
    )


def downgrade() -> None:
    op.drop_table("furniture_dimensions")
