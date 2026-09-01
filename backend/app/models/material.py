"""Admin-managed material catalog item."""

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum as SAEnum,
    String,
    UniqueConstraint,
    Uuid,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import MaterialType, MaterialUnit
from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.material_price import MaterialPrice


class Material(TimestampMixin, Base):
    """A wood or hardware item with one stable administrative unit."""

    __tablename__ = "materials"
    __table_args__ = (
        UniqueConstraint("material_name", name="uq_materials_material_name"),
        CheckConstraint(
            "material_type IN ('wood', 'hardware')",
            name="type_allowed",
        ),
        CheckConstraint(
            "unit IN ('mm3', 'cm3', 'm3', 'board_ft', 'piece')",
            name="unit_allowed",
        ),
        CheckConstraint(
            "(material_type = 'wood' AND "
            "unit IN ('mm3', 'cm3', 'm3', 'board_ft')) OR "
            "(material_type = 'hardware' AND unit = 'piece')",
            name="type_unit_compatible",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    material_name: Mapped[str] = mapped_column(String(200), nullable=False)
    material_type: Mapped[MaterialType] = mapped_column(
        SAEnum(
            MaterialType,
            name="material_type_values",
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            length=16,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
        index=True,
    )
    unit: Mapped[MaterialUnit] = mapped_column(
        SAEnum(
            MaterialUnit,
            name="material_unit_values",
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            length=16,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
        index=True,
    )

    prices: Mapped[list["MaterialPrice"]] = relationship(
        back_populates="material",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by=(
            "(MaterialPrice.effective_date.desc(), MaterialPrice.created_at.desc(), "
            "MaterialPrice.id.desc())"
        ),
    )
