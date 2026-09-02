"""Add photo-derived reconstruction proposals and component provenance.

Revision ID: 20260902_0010
Revises: 20260902_0009
Create Date: 2026-09-02
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260902_0010"
down_revision: str | None = "20260902_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "furniture_reconstructions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("furniture_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("input_signature", sa.String(length=64), nullable=False),
        sa.Column("furniture_type", sa.String(length=32), nullable=False),
        sa.Column("provider_name", sa.String(length=100), nullable=False),
        sa.Column("provider_version", sa.String(length=100), nullable=True),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("warnings", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name=op.f("ck_furniture_reconstructions_confidence_range")),
        sa.CheckConstraint("furniture_type IN ('chair', 'dining_table', 'bookshelf')", name=op.f("ck_furniture_reconstructions_furniture_type_allowed")),
        sa.CheckConstraint("char_length(input_signature) = 64", name=op.f("ck_furniture_reconstructions_input_signature_length")),
        sa.ForeignKeyConstraint(["furniture_id"], ["furniture.id"], name=op.f("fk_furniture_reconstructions_furniture_id_furniture"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_furniture_reconstructions")),
        sa.UniqueConstraint("furniture_id", name="uq_furniture_reconstructions_furniture_id"),
    )
    op.create_index(op.f("ix_furniture_reconstructions_furniture_id"), "furniture_reconstructions", ["furniture_id"], unique=False)

    op.create_table(
        "furniture_reconstruction_parts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reconstruction_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("component_name", sa.String(length=200), nullable=False),
        sa.Column("component_type", sa.String(length=16), nullable=False),
        sa.Column("geometry_kind", sa.String(length=32), nullable=False),
        sa.Column("profile_points", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("width", sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column("height", sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column("depth", sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column("x", sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column("y", sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column("z", sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column("rotation_x", sa.Numeric(precision=9, scale=4), nullable=False),
        sa.Column("rotation_y", sa.Numeric(precision=9, scale=4), nullable=False),
        sa.Column("rotation_z", sa.Numeric(precision=9, scale=4), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("source_views", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("component_type IN ('panel', 'leg')", name=op.f("ck_furniture_reconstruction_parts_type_allowed")),
        sa.CheckConstraint("width > 0 AND height > 0 AND depth > 0", name=op.f("ck_furniture_reconstruction_parts_dimensions_positive")),
        sa.CheckConstraint("quantity > 0", name=op.f("ck_furniture_reconstruction_parts_quantity_positive")),
        sa.CheckConstraint("sort_order >= 0", name=op.f("ck_furniture_reconstruction_parts_sort_order_nonnegative")),
        sa.CheckConstraint("geometry_kind IN ('box', 'extruded_profile')", name=op.f("ck_furniture_reconstruction_parts_geometry_kind_allowed")),
        sa.CheckConstraint("(geometry_kind = 'box' AND profile_points IS NULL) OR (geometry_kind = 'extruded_profile' AND profile_points IS NOT NULL AND jsonb_typeof(profile_points) = 'array' AND jsonb_array_length(profile_points) >= 3)", name=op.f("ck_furniture_reconstruction_parts_profile_consistent")),
        sa.CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name=op.f("ck_furniture_reconstruction_parts_confidence_range")),
        sa.ForeignKeyConstraint(["reconstruction_id"], ["furniture_reconstructions.id"], name=op.f("fk_furniture_reconstruction_parts_reconstruction_id_furniture_reconstructions"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_furniture_reconstruction_parts")),
    )
    op.create_index(op.f("ix_furniture_reconstruction_parts_reconstruction_id"), "furniture_reconstruction_parts", ["reconstruction_id"], unique=False)

    op.add_column("furniture_plans", sa.Column("source_reconstruction_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(op.f("fk_furniture_plans_source_reconstruction_id_furniture_reconstructions"), "furniture_plans", "furniture_reconstructions", ["source_reconstruction_id"], ["id"], ondelete="SET NULL")
    op.create_index(op.f("ix_furniture_plans_source_reconstruction_id"), "furniture_plans", ["source_reconstruction_id"], unique=False)

    op.add_column("furniture_components", sa.Column("source_reconstruction_part_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("furniture_components", sa.Column("rotation_x", sa.Numeric(precision=9, scale=4), server_default="0", nullable=False))
    op.add_column("furniture_components", sa.Column("rotation_y", sa.Numeric(precision=9, scale=4), server_default="0", nullable=False))
    op.add_column("furniture_components", sa.Column("rotation_z", sa.Numeric(precision=9, scale=4), server_default="0", nullable=False))
    op.add_column("furniture_components", sa.Column("geometry_kind", sa.String(length=32), server_default="box", nullable=False))
    op.add_column("furniture_components", sa.Column("profile_points", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("furniture_components", sa.Column("source_confidence", sa.Numeric(precision=5, scale=4), nullable=True))
    op.add_column("furniture_components", sa.Column("source_views", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False))
    op.create_foreign_key(op.f("fk_furniture_components_source_reconstruction_part_id_furniture_reconstruction_parts"), "furniture_components", "furniture_reconstruction_parts", ["source_reconstruction_part_id"], ["id"], ondelete="SET NULL")
    op.create_index(op.f("ix_furniture_components_source_reconstruction_part_id"), "furniture_components", ["source_reconstruction_part_id"], unique=False)
    op.create_check_constraint(op.f("ck_furniture_components_geometry_kind_allowed"), "furniture_components", "geometry_kind IN ('box', 'extruded_profile')")
    op.create_check_constraint(op.f("ck_furniture_components_profile_consistent"), "furniture_components", "(geometry_kind = 'box' AND profile_points IS NULL) OR (geometry_kind = 'extruded_profile' AND profile_points IS NOT NULL AND jsonb_typeof(profile_points) = 'array' AND jsonb_array_length(profile_points) >= 3)")
    op.create_check_constraint(op.f("ck_furniture_components_source_confidence_range"), "furniture_components", "source_confidence IS NULL OR (source_confidence >= 0 AND source_confidence <= 1)")


def downgrade() -> None:
    op.drop_constraint(op.f("ck_furniture_components_source_confidence_range"), "furniture_components", type_="check")
    op.drop_constraint(op.f("ck_furniture_components_profile_consistent"), "furniture_components", type_="check")
    op.drop_constraint(op.f("ck_furniture_components_geometry_kind_allowed"), "furniture_components", type_="check")
    op.drop_index(op.f("ix_furniture_components_source_reconstruction_part_id"), table_name="furniture_components")
    op.drop_constraint(op.f("fk_furniture_components_source_reconstruction_part_id_furniture_reconstruction_parts"), "furniture_components", type_="foreignkey")
    for column in ("source_views", "source_confidence", "profile_points", "geometry_kind", "rotation_z", "rotation_y", "rotation_x", "source_reconstruction_part_id"):
        op.drop_column("furniture_components", column)
    op.drop_index(op.f("ix_furniture_plans_source_reconstruction_id"), table_name="furniture_plans")
    op.drop_constraint(op.f("fk_furniture_plans_source_reconstruction_id_furniture_reconstructions"), "furniture_plans", type_="foreignkey")
    op.drop_column("furniture_plans", "source_reconstruction_id")
    op.drop_index(op.f("ix_furniture_reconstruction_parts_reconstruction_id"), table_name="furniture_reconstruction_parts")
    op.drop_table("furniture_reconstruction_parts")
    op.drop_index(op.f("ix_furniture_reconstructions_furniture_id"), table_name="furniture_reconstructions")
    op.drop_table("furniture_reconstructions")
