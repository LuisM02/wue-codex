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
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ComponentType, GeometryKind
from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.furniture_plan import FurniturePlan
    from app.models.furniture_reconstruction_part import FurnitureReconstructionPart


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
        CheckConstraint(
            "geometry_kind IN ('box', 'extruded_profile')",
            name="geometry_kind_allowed",
        ),
        CheckConstraint(
            "(geometry_kind = 'box' AND profile_points IS NULL) OR "
            "(geometry_kind = 'extruded_profile' AND profile_points IS NOT NULL "
            "AND jsonb_typeof(profile_points) = 'array' "
            "AND jsonb_array_length(profile_points) >= 3)",
            name="profile_consistent",
        ),
        CheckConstraint(
            "source_confidence IS NULL OR "
            "(source_confidence >= 0 AND source_confidence <= 1)",
            name="source_confidence_range",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    plan_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("furniture_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_reconstruction_part_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("furniture_reconstruction_parts.id", ondelete="SET NULL"),
        nullable=True,
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
    rotation_x: Mapped[Decimal] = mapped_column(
        Numeric(9, 4), nullable=False, default=Decimal("0"), server_default="0"
    )
    rotation_y: Mapped[Decimal] = mapped_column(
        Numeric(9, 4), nullable=False, default=Decimal("0"), server_default="0"
    )
    rotation_z: Mapped[Decimal] = mapped_column(
        Numeric(9, 4), nullable=False, default=Decimal("0"), server_default="0"
    )
    geometry_kind: Mapped[GeometryKind] = mapped_column(
        SAEnum(
            GeometryKind,
            name="geometry_kind_values",
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            length=32,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
        default=GeometryKind.BOX,
        server_default=GeometryKind.BOX.value,
    )
    profile_points: Mapped[list[dict[str, str]] | None] = mapped_column(
        JSONB(none_as_null=True), nullable=True
    )
    source_confidence: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4), nullable=True
    )
    source_views: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)

    plan: Mapped["FurniturePlan"] = relationship(back_populates="components")
    source_reconstruction_part: Mapped["FurnitureReconstructionPart | None"] = relationship(
        back_populates="plan_components"
    )
