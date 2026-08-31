"""Create furniture classifications.

Revision ID: 20260831_0003
Revises: 20260831_0002
Create Date: 2026-08-31
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260831_0003"
down_revision: str | None = "20260831_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "furniture_classifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("furniture_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("predicted_type", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("classifier_name", sa.String(length=100), nullable=False),
        sa.Column("classifier_version", sa.String(length=100), nullable=True),
        sa.Column("input_signature", sa.String(length=64), nullable=False),
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
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name=op.f("ck_furniture_classifications_confidence_range"),
        ),
        sa.CheckConstraint(
            "predicted_type IN ('chair', 'dining_table', 'bookshelf')",
            name=op.f("ck_furniture_classifications_predicted_type_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["furniture_id"],
            ["furniture.id"],
            name=op.f("fk_furniture_classifications_furniture_id_furniture"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_furniture_classifications"),
        ),
        sa.UniqueConstraint(
            "furniture_id",
            name="uq_furniture_classifications_furniture_id",
        ),
    )


def downgrade() -> None:
    op.drop_table("furniture_classifications")
