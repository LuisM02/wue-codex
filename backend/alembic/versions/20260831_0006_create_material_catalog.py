"""Create material catalog and dated price history.

Revision ID: 20260831_0006
Revises: 20260831_0005
Create Date: 2026-08-31
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260831_0006"
down_revision: str | None = "20260831_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "materials",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("material_name", sa.String(length=200), nullable=False),
        sa.Column("material_type", sa.String(length=16), nullable=False),
        sa.Column("unit", sa.String(length=16), nullable=False),
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
        sa.CheckConstraint(
            "material_type IN ('wood', 'hardware')",
            name=op.f("ck_materials_type_allowed"),
        ),
        sa.CheckConstraint(
            "(material_type = 'wood' AND "
            "unit IN ('mm3', 'cm3', 'm3', 'board_ft')) OR "
            "(material_type = 'hardware' AND unit = 'piece')",
            name=op.f("ck_materials_type_unit_compatible"),
        ),
        sa.CheckConstraint(
            "unit IN ('mm3', 'cm3', 'm3', 'board_ft', 'piece')",
            name=op.f("ck_materials_unit_allowed"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_materials")),
        sa.UniqueConstraint(
            "material_name",
            name="uq_materials_material_name",
        ),
    )
    op.create_index(
        op.f("ix_materials_is_active"),
        "materials",
        ["is_active"],
        unique=False,
    )
    op.create_index(
        op.f("ix_materials_material_type"),
        "materials",
        ["material_type"],
        unique=False,
    )

    op.create_table(
        "material_prices",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("material_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "price_per_unit",
            sa.Numeric(precision=18, scale=6),
            nullable=False,
        ),
        sa.Column("unit", sa.String(length=16), nullable=False),
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
            "price_per_unit >= 0",
            name=op.f("ck_material_prices_price_nonnegative"),
        ),
        sa.CheckConstraint(
            "unit IN ('mm3', 'cm3', 'm3', 'board_ft', 'piece')",
            name=op.f("ck_material_prices_unit_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["material_id"],
            ["materials.id"],
            name=op.f("fk_material_prices_material_id_materials"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_material_prices")),
    )
    op.create_index(
        op.f("ix_material_prices_effective_date"),
        "material_prices",
        ["effective_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_material_prices_material_id"),
        "material_prices",
        ["material_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_material_prices_material_id"),
        table_name="material_prices",
    )
    op.drop_index(
        op.f("ix_material_prices_effective_date"),
        table_name="material_prices",
    )
    op.drop_table("material_prices")
    op.drop_index(
        op.f("ix_materials_material_type"),
        table_name="materials",
    )
    op.drop_index(
        op.f("ix_materials_is_active"),
        table_name="materials",
    )
    op.drop_table("materials")
