"""Create furniture image metadata.

Revision ID: 20260831_0002
Revises: 20260831_0001
Create Date: 2026-08-31
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260831_0002"
down_revision: str | None = "20260831_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "furniture_images",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("furniture_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("view", sa.String(length=16), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=32), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("pixel_width", sa.Integer(), nullable=False),
        sa.Column("pixel_height", sa.Integer(), nullable=False),
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
            "content_type IN ('image/jpeg', 'image/png', 'image/webp')",
            name=op.f("ck_furniture_images_content_type_allowed"),
        ),
        sa.CheckConstraint(
            "file_size_bytes > 0",
            name=op.f("ck_furniture_images_file_size_positive"),
        ),
        sa.CheckConstraint(
            "pixel_width > 0 AND pixel_height > 0",
            name=op.f("ck_furniture_images_pixel_dimensions_positive"),
        ),
        sa.CheckConstraint(
            "source IN ('upload', 'camera_capture')",
            name=op.f("ck_furniture_images_source_allowed"),
        ),
        sa.CheckConstraint(
            "view IN ('front', 'back', 'left', 'right', 'top')",
            name=op.f("ck_furniture_images_view_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["furniture_id"],
            ["furniture.id"],
            name=op.f("fk_furniture_images_furniture_id_furniture"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_furniture_images")),
        sa.UniqueConstraint(
            "furniture_id",
            "view",
            name="uq_furniture_images_furniture_id_view",
        ),
        sa.UniqueConstraint(
            "storage_key",
            name="uq_furniture_images_storage_key",
        ),
    )


def downgrade() -> None:
    op.drop_table("furniture_images")
