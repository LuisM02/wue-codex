"""Allow furniture to remain unclassified until image analysis.

Revision ID: 20260902_0009
Revises: 20260901_0008
Create Date: 2026-09-02
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260902_0009"
down_revision: str | None = "20260901_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "furniture",
        "furniture_type",
        existing_type=sa.String(length=32),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "furniture",
        "furniture_type",
        existing_type=sa.String(length=32),
        nullable=False,
    )
