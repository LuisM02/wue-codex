"""Create versioned parametric furniture plans and components.

Revision ID: 20260831_0005
Revises: 20260831_0004
Create Date: 2026-08-31
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260831_0005"
down_revision: str | None = "20260831_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "furniture_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("furniture_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("furniture_type", sa.String(length=32), nullable=False),
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
            "furniture_type IN ('chair', 'dining_table', 'bookshelf')",
            name=op.f("ck_furniture_plans_furniture_type_allowed"),
        ),
        sa.CheckConstraint(
            "revision > 0",
            name=op.f("ck_furniture_plans_revision_positive"),
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'finalized')",
            name=op.f("ck_furniture_plans_status_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["furniture_id"],
            ["furniture.id"],
            name=op.f("fk_furniture_plans_furniture_id_furniture"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_furniture_plans")),
        sa.UniqueConstraint(
            "furniture_id",
            "revision",
            name="uq_furniture_plans_furniture_revision",
        ),
    )
    op.create_index(
        op.f("ix_furniture_plans_furniture_id"),
        "furniture_plans",
        ["furniture_id"],
        unique=False,
    )
    op.create_index(
        "uq_furniture_plans_one_draft_per_furniture",
        "furniture_plans",
        ["furniture_id"],
        unique=True,
        postgresql_where=sa.text("status = 'draft'"),
    )

    op.create_table(
        "furniture_components",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("component_name", sa.String(length=200), nullable=False),
        sa.Column("component_type", sa.String(length=16), nullable=False),
        sa.Column("width", sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column("height", sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column("depth", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("thickness", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("x", sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column("y", sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column("z", sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column("rotation", sa.Numeric(precision=9, scale=4), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
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
            "depth IS NULL OR depth > 0",
            name=op.f("ck_furniture_components_depth_positive"),
        ),
        sa.CheckConstraint(
            "width > 0 AND height > 0",
            name=op.f("ck_furniture_components_dimensions_positive"),
        ),
        sa.CheckConstraint(
            "quantity > 0",
            name=op.f("ck_furniture_components_quantity_positive"),
        ),
        sa.CheckConstraint(
            "sort_order >= 0",
            name=op.f("ck_furniture_components_sort_order_nonnegative"),
        ),
        sa.CheckConstraint(
            "thickness IS NULL OR thickness > 0",
            name=op.f("ck_furniture_components_thickness_positive"),
        ),
        sa.CheckConstraint(
            "component_type IN ('panel', 'leg')",
            name=op.f("ck_furniture_components_type_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["furniture_plans.id"],
            name=op.f("fk_furniture_components_plan_id_furniture_plans"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_furniture_components")),
    )
    op.create_index(
        op.f("ix_furniture_components_plan_id"),
        "furniture_components",
        ["plan_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_furniture_components_plan_id"),
        table_name="furniture_components",
    )
    op.drop_table("furniture_components")
    op.drop_index(
        "uq_furniture_plans_one_draft_per_furniture",
        table_name="furniture_plans",
        postgresql_where=sa.text("status = 'draft'"),
    )
    op.drop_index(
        op.f("ix_furniture_plans_furniture_id"),
        table_name="furniture_plans",
    )
    op.drop_table("furniture_plans")
