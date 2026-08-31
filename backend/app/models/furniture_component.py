"""Editable component geometry belonging to a furniture plan."""

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
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ComponentType
from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.furniture_plan import FurniturePlan


class FurnitureComponent(TimestampMixin, Base):
    """Canonical X/Y/Z rectangular component geometry in millimeters."""

    __tablename__ = "furniture_components"
    __table_args__ = (
        CheckConstraint("component_type IN ('panel', 'leg')", name="type_allowed"),
        CheckConstraint("width > 0 AND height > 0", name="dimensions_positive"),
        CheckConstraint("depth IS NULL OR depth > 0", name="depth_positive"),
        CheckConstraint("thickness IS NULL OR thickness > 0", name="thickness_positive"),
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("sort_order >= 0", name="sort_order_nonnegative"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    plan_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("furniture_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    component_name: Mapped[str] = mapped_column(String(200), nullable=False)
    component_type: Mapped[ComponentType] = mapped_column(
        SAEnum(
            ComponentType,
            name="component_type_values",
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            length=16,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
    )
    width: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    height: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    depth: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    thickness: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    x: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    y: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    z: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    rotation: Mapped[Decimal] = mapped_column(Numeric(9, 4), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)

    plan: Mapped["FurniturePlan"] = relationship(back_populates="components")
