"""AI-detected editable parts belonging to a photo reconstruction."""

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Enum as SAEnum, ForeignKey, Integer, Numeric, String, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ComponentType, GeometryKind
from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.furniture_component import FurnitureComponent
    from app.models.furniture_reconstruction import FurnitureReconstruction


class FurnitureReconstructionPart(TimestampMixin, Base):
    """One semantic part inferred from the exact uploaded photographs."""

    __tablename__ = "furniture_reconstruction_parts"
    __table_args__ = (
        CheckConstraint("component_type IN ('panel', 'leg')", name="type_allowed"),
        CheckConstraint("width > 0 AND height > 0 AND depth > 0", name="dimensions_positive"),
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("sort_order >= 0", name="sort_order_nonnegative"),
        CheckConstraint("geometry_kind IN ('box', 'extruded_profile')", name="geometry_kind_allowed"),
        CheckConstraint(
            "(geometry_kind = 'box' AND profile_points IS NULL) OR "
            "(geometry_kind = 'extruded_profile' AND profile_points IS NOT NULL "
            "AND jsonb_typeof(profile_points) = 'array' "
            "AND jsonb_array_length(profile_points) >= 3)",
            name="profile_consistent",
        ),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="confidence_range",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    reconstruction_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("furniture_reconstructions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    component_name: Mapped[str] = mapped_column(String(200), nullable=False)
    component_type: Mapped[ComponentType] = mapped_column(
        SAEnum(
            ComponentType,
            name="reconstruction_component_type_values",
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            length=16,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
    )
    geometry_kind: Mapped[GeometryKind] = mapped_column(
        SAEnum(
            GeometryKind,
            name="reconstruction_geometry_kind_values",
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            length=32,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
    )
    profile_points: Mapped[list[dict[str, str]] | None] = mapped_column(
        JSONB(none_as_null=True), nullable=True
    )
    width: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    height: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    depth: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    x: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    y: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    z: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    rotation_x: Mapped[Decimal] = mapped_column(Numeric(9, 4), nullable=False, default=Decimal("0"))
    rotation_y: Mapped[Decimal] = mapped_column(Numeric(9, 4), nullable=False, default=Decimal("0"))
    rotation_z: Mapped[Decimal] = mapped_column(Numeric(9, 4), nullable=False, default=Decimal("0"))
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    source_views: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )

    reconstruction: Mapped["FurnitureReconstruction"] = relationship(back_populates="parts")
    plan_components: Mapped[list["FurnitureComponent"]] = relationship(
        back_populates="source_reconstruction_part",
        passive_deletes=True,
    )
