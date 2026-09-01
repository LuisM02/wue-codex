"""Create immutable quotation snapshots.

Revision ID: 20260901_0008
Revises: 20260901_0007
Create Date: 2026-09-01
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260901_0008"
down_revision: str | None = "20260901_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "quotations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quotation_number", sa.String(length=40), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("furniture_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_revision", sa.Integer(), nullable=False),
        sa.Column("furniture_type", sa.String(length=32), nullable=False),
        sa.Column("wood_material_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("wood_material_name", sa.String(length=200), nullable=False),
        sa.Column("wood_price_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("wood_price_per_unit", sa.Numeric(), nullable=False),
        sa.Column("wood_price_unit", sa.String(length=16), nullable=False),
        sa.Column("wood_price_effective_date", sa.Date(), nullable=False),
        sa.Column("wood_quantity", sa.Numeric(), nullable=False),
        sa.Column("wood_material_cost", sa.Numeric(), nullable=False),
        sa.Column("hardware_material_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("hardware_material_name", sa.String(length=200), nullable=False),
        sa.Column("hardware_price_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("hardware_price_per_piece", sa.Numeric(), nullable=False),
        sa.Column("hardware_price_effective_date", sa.Date(), nullable=False),
        sa.Column("hardware_quantity", sa.Integer(), nullable=False),
        sa.Column("hardware_cost", sa.Numeric(), nullable=False),
        sa.Column("labor_rate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("labor_rate_name", sa.String(length=200), nullable=False),
        sa.Column("labor_rate_price_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("labor_rate_per_hour", sa.Numeric(), nullable=False),
        sa.Column("labor_rate_effective_date", sa.Date(), nullable=False),
        sa.Column("labor_hours", sa.Numeric(), nullable=False),
        sa.Column("labor_cost", sa.Numeric(), nullable=False),
        sa.Column("total_cost", sa.Numeric(), nullable=False),
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
            "wood_material_cost >= 0 AND hardware_cost >= 0 "
            "AND labor_cost >= 0 AND total_cost >= 0",
            name=op.f("ck_quotations_costs_nonnegative"),
        ),
        sa.CheckConstraint(
            "furniture_type IN ('chair', 'dining_table', 'bookshelf')",
            name=op.f("ck_quotations_furniture_type_allowed"),
        ),
        sa.CheckConstraint(
            "plan_revision > 0",
            name=op.f("ck_quotations_revision_positive"),
        ),
        sa.CheckConstraint(
            "wood_quantity >= 0 AND hardware_quantity >= 0 "
            "AND labor_hours >= 0",
            name=op.f("ck_quotations_quantities_nonnegative"),
        ),
        sa.CheckConstraint(
            "wood_price_per_unit >= 0 AND hardware_price_per_piece >= 0 "
            "AND labor_rate_per_hour >= 0",
            name=op.f("ck_quotations_rates_nonnegative"),
        ),
        sa.CheckConstraint(
            "total_cost = wood_material_cost + hardware_cost + labor_cost",
            name=op.f("ck_quotations_total_matches_components"),
        ),
        sa.CheckConstraint(
            "wood_price_unit IN ('mm3', 'cm3', 'm3', 'board_ft')",
            name=op.f("ck_quotations_wood_price_unit_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["furniture_plans.id"],
            name=op.f("fk_quotations_plan_id_furniture_plans"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quotations")),
        sa.UniqueConstraint(
            "quotation_number",
            name="uq_quotations_quotation_number",
        ),
    )
    for column_name in ("furniture_id", "plan_id", "project_id"):
        op.create_index(
            op.f(f"ix_quotations_{column_name}"),
            "quotations",
            [column_name],
            unique=False,
        )


def downgrade() -> None:
    for column_name in ("project_id", "plan_id", "furniture_id"):
        op.drop_index(
            op.f(f"ix_quotations_{column_name}"),
            table_name="quotations",
        )
    op.drop_table("quotations")
