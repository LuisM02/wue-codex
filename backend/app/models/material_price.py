"""Dated administrative material price history."""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Enum as SAEnum, ForeignKey, Numeric, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import MaterialUnit
from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.material import Material


class MaterialPrice(TimestampMixin, Base):
    """One price per administrative unit, effective on a supplied date."""

    __tablename__ = "material_prices"
    __table_args__ = (
        CheckConstraint("price_per_unit >= 0", name="price_nonnegative"),
        CheckConstraint(
            "unit IN ('mm3', 'cm3', 'm3', 'board_ft', 'piece')",
            name="unit_allowed",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    material_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("materials.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    price_per_unit: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    unit: Mapped[MaterialUnit] = mapped_column(
        SAEnum(
            MaterialUnit,
            name="material_price_unit_values",
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            length=16,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
    )
    effective_date: Mapped[date] = mapped_column(nullable=False, index=True)

    material: Mapped["Material"] = relationship(back_populates="prices")
