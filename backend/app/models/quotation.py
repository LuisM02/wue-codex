"""Immutable quotation snapshot generated from a finalized plan."""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import FurnitureType, MaterialUnit
from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.furniture_plan import FurniturePlan


class Quotation(TimestampMixin, Base):
    """A historical cost snapshot; later catalog changes do not rewrite it."""

    __tablename__ = "quotations"
    __table_args__ = (
        UniqueConstraint(
            "quotation_number",
            name="uq_quotations_quotation_number",
        ),
        CheckConstraint("plan_revision > 0", name="revision_positive"),
        CheckConstraint(
            "furniture_type IN ('chair', 'dining_table', 'bookshelf')",
            name="furniture_type_allowed",
        ),
        CheckConstraint(
            "wood_price_unit IN ('mm3', 'cm3', 'm3', 'board_ft')",
            name="wood_price_unit_allowed",
        ),
        CheckConstraint(
            "wood_quantity >= 0 AND hardware_quantity >= 0 "
            "AND labor_hours >= 0",
            name="quantities_nonnegative",
        ),
        CheckConstraint(
            "wood_price_per_unit >= 0 AND hardware_price_per_piece >= 0 "
            "AND labor_rate_per_hour >= 0",
            name="rates_nonnegative",
        ),
        CheckConstraint(
            "wood_material_cost >= 0 AND hardware_cost >= 0 "
            "AND labor_cost >= 0 AND total_cost >= 0",
            name="costs_nonnegative",
        ),
        CheckConstraint(
            "total_cost = wood_material_cost + hardware_cost + labor_cost",
            name="total_matches_components",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    quotation_number: Mapped[str] = mapped_column(String(40), nullable=False)
    project_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    furniture_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    plan_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("furniture_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plan_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    furniture_type: Mapped[FurnitureType] = mapped_column(
        SAEnum(
            FurnitureType,
            name="quotation_furniture_type_values",
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            length=32,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
    )

    wood_material_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    wood_material_name: Mapped[str] = mapped_column(String(200), nullable=False)
    wood_price_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    wood_price_per_unit: Mapped[Decimal] = mapped_column(Numeric(), nullable=False)
    wood_price_unit: Mapped[MaterialUnit] = mapped_column(
        SAEnum(
            MaterialUnit,
            name="quotation_material_unit_values",
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            length=16,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
    )
    wood_price_effective_date: Mapped[date] = mapped_column(nullable=False)
    wood_quantity: Mapped[Decimal] = mapped_column(Numeric(), nullable=False)
    wood_material_cost: Mapped[Decimal] = mapped_column(Numeric(), nullable=False)

    hardware_material_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    hardware_material_name: Mapped[str] = mapped_column(String(200), nullable=False)
    hardware_price_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    hardware_price_per_piece: Mapped[Decimal] = mapped_column(Numeric(), nullable=False)
    hardware_price_effective_date: Mapped[date] = mapped_column(nullable=False)
    hardware_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    hardware_cost: Mapped[Decimal] = mapped_column(Numeric(), nullable=False)

    labor_rate_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    labor_rate_name: Mapped[str] = mapped_column(String(200), nullable=False)
    labor_rate_price_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    labor_rate_per_hour: Mapped[Decimal] = mapped_column(Numeric(), nullable=False)
    labor_rate_effective_date: Mapped[date] = mapped_column(nullable=False)
    labor_hours: Mapped[Decimal] = mapped_column(Numeric(), nullable=False)
    labor_cost: Mapped[Decimal] = mapped_column(Numeric(), nullable=False)

    total_cost: Mapped[Decimal] = mapped_column(Numeric(), nullable=False)

    plan: Mapped["FurniturePlan"] = relationship(back_populates="quotations")
