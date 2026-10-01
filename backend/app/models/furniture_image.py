"""Furniture image metadata ORM model."""

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
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

from app.core.enums import FurnitureImageView, ImageInputSource
from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.furniture import Furniture


class FurnitureImage(TimestampMixin, Base):
    """Metadata for one required photographic view of a furniture item."""

    __tablename__ = "furniture_images"
    __table_args__ = (
        UniqueConstraint(
            "furniture_id",
            "view",
            name="uq_furniture_images_furniture_id_view",
        ),
        UniqueConstraint(
            "storage_key",
            name="uq_furniture_images_storage_key",
        ),
        CheckConstraint(
            "view IN ('front', 'back', 'left', 'right', 'top')",
            name="view_allowed",
        ),
        CheckConstraint(
            "source IN ('upload', 'camera_capture')",
            name="source_allowed",
        ),
        CheckConstraint(
            "content_type IN ('image/jpeg', 'image/png', 'image/webp')",
            name="content_type_allowed",
        ),
        CheckConstraint("file_size_bytes > 0", name="file_size_positive"),
        CheckConstraint(
            "pixel_width > 0 AND pixel_height > 0",
            name="pixel_dimensions_positive",
        ),
        CheckConstraint(
            "object_left_ratio >= 0 AND object_left_ratio < 1",
            name="object_left_ratio_range",
        ),
        CheckConstraint(
            "object_top_ratio >= 0 AND object_top_ratio < 1",
            name="object_top_ratio_range",
        ),
        CheckConstraint(
            "object_width_ratio > 0 AND object_width_ratio <= 1",
            name="object_width_ratio_range",
        ),
        CheckConstraint(
            "object_height_ratio > 0 AND object_height_ratio <= 1",
            name="object_height_ratio_range",
        ),
        CheckConstraint(
            "object_left_ratio + object_width_ratio <= 1",
            name="object_horizontal_crop_inside_image",
        ),
        CheckConstraint(
            "object_top_ratio + object_height_ratio <= 1",
            name="object_vertical_crop_inside_image",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    furniture_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("furniture.id", ondelete="CASCADE"),
        nullable=False,
    )
    view: Mapped[FurnitureImageView] = mapped_column(
        SAEnum(
            FurnitureImageView,
            name="furniture_image_view_values",
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            length=16,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
    )
    source: Mapped[ImageInputSource] = mapped_column(
        SAEnum(
            ImageInputSource,
            name="image_input_source_values",
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            length=32,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
    )
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(32), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    pixel_width: Mapped[int] = mapped_column(Integer, nullable=False)
    pixel_height: Mapped[int] = mapped_column(Integer, nullable=False)
    object_left_ratio: Mapped[Decimal] = mapped_column(
        Numeric(7, 6), nullable=False, default=Decimal("0"), server_default="0"
    )
    object_top_ratio: Mapped[Decimal] = mapped_column(
        Numeric(7, 6), nullable=False, default=Decimal("0"), server_default="0"
    )
    object_width_ratio: Mapped[Decimal] = mapped_column(
        Numeric(7, 6), nullable=False, default=Decimal("1"), server_default="1"
    )
    object_height_ratio: Mapped[Decimal] = mapped_column(
        Numeric(7, 6), nullable=False, default=Decimal("1"), server_default="1"
    )
    is_mirrored: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    furniture: Mapped["Furniture"] = relationship(back_populates="images")
