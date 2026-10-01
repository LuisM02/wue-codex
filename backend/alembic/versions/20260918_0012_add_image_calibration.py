"""Add metric alignment calibration to furniture images.

Revision ID: 20260918_0012
Revises: 20260918_0011
Create Date: 2026-09-18
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260918_0012"
down_revision: str | None = "20260918_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("furniture_images", sa.Column("object_left_ratio", sa.Numeric(7, 6), server_default="0", nullable=False))
    op.add_column("furniture_images", sa.Column("object_top_ratio", sa.Numeric(7, 6), server_default="0", nullable=False))
    op.add_column("furniture_images", sa.Column("object_width_ratio", sa.Numeric(7, 6), server_default="1", nullable=False))
    op.add_column("furniture_images", sa.Column("object_height_ratio", sa.Numeric(7, 6), server_default="1", nullable=False))
    op.add_column("furniture_images", sa.Column("is_mirrored", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.create_check_constraint(op.f("ck_furniture_images_object_left_ratio_range"), "furniture_images", "object_left_ratio >= 0 AND object_left_ratio < 1")
    op.create_check_constraint(op.f("ck_furniture_images_object_top_ratio_range"), "furniture_images", "object_top_ratio >= 0 AND object_top_ratio < 1")
    op.create_check_constraint(op.f("ck_furniture_images_object_width_ratio_range"), "furniture_images", "object_width_ratio > 0 AND object_width_ratio <= 1")
    op.create_check_constraint(op.f("ck_furniture_images_object_height_ratio_range"), "furniture_images", "object_height_ratio > 0 AND object_height_ratio <= 1")
    op.create_check_constraint(op.f("ck_furniture_images_object_horizontal_crop_inside_image"), "furniture_images", "object_left_ratio + object_width_ratio <= 1")
    op.create_check_constraint(op.f("ck_furniture_images_object_vertical_crop_inside_image"), "furniture_images", "object_top_ratio + object_height_ratio <= 1")


def downgrade() -> None:
    op.drop_constraint(op.f("ck_furniture_images_object_vertical_crop_inside_image"), "furniture_images", type_="check")
    op.drop_constraint(op.f("ck_furniture_images_object_horizontal_crop_inside_image"), "furniture_images", type_="check")
    op.drop_constraint(op.f("ck_furniture_images_object_height_ratio_range"), "furniture_images", type_="check")
    op.drop_constraint(op.f("ck_furniture_images_object_width_ratio_range"), "furniture_images", type_="check")
    op.drop_constraint(op.f("ck_furniture_images_object_top_ratio_range"), "furniture_images", type_="check")
    op.drop_constraint(op.f("ck_furniture_images_object_left_ratio_range"), "furniture_images", type_="check")
    op.drop_column("furniture_images", "is_mirrored")
    op.drop_column("furniture_images", "object_height_ratio")
    op.drop_column("furniture_images", "object_width_ratio")
    op.drop_column("furniture_images", "object_top_ratio")
    op.drop_column("furniture_images", "object_left_ratio")
