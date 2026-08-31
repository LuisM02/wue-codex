"""Canonical overall furniture dimensions."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Numeric,
    UniqueConstraint,
    Uuid,
    false,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import DimensionSource, DimensionUnit
from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.furniture import Furniture


class FurnitureDimensions(TimestampMixin, Base):
    """Width=X, height=Y, and depth=Z stored in canonical millimeters."""

    __tablename__ = "furniture_dimensions"
    __table_args__ = (
        UniqueConstraint(
            "furniture_id",
            name="uq_furniture_dimensions_furniture_id",
        ),
        CheckConstraint(
            "width_mm > 0 AND height_mm > 0 AND depth_mm > 0",
            name="values_positive",
        ),
        CheckConstraint(
            "unit IN ('mm', 'cm', 'm', 'in')",
            name="unit_allowed",
        ),
        CheckConstraint(
            "source IN ('manual', 'ai_estimate')",
            name="source_allowed",
        ),
        CheckConstraint(
            "(is_locked = false AND locked_at IS NULL) OR "
            "(is_locked = true AND locked_at IS NOT NULL)",
            name="lock_state_consistent",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    furniture_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("furniture.id", ondelete="CASCADE"),
        nullable=False,
    )
    width_mm: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    height_mm: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    depth_mm: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    unit: Mapped[DimensionUnit] = mapped_column(
        SAEnum(
            DimensionUnit,
            name="dimension_unit_values",
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            length=4,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
    )
    source: Mapped[DimensionSource] = mapped_column(
        SAEnum(
            DimensionSource,
            name="dimension_source_values",
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            length=16,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
    )
    is_locked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    furniture: Mapped["Furniture"] = relationship(back_populates="dimensions")
