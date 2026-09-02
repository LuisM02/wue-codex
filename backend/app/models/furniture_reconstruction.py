"""Persisted result of photo-derived furniture reconstruction."""

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Enum as SAEnum, ForeignKey, Numeric, String, UniqueConstraint, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import FurnitureType
from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.furniture import Furniture
    from app.models.furniture_plan import FurniturePlan
    from app.models.furniture_reconstruction_part import FurnitureReconstructionPart


class FurnitureReconstruction(TimestampMixin, Base):
    """Latest validated AI proposal for one exact five-photo set."""

    __tablename__ = "furniture_reconstructions"
    __table_args__ = (
        UniqueConstraint("furniture_id", name="uq_furniture_reconstructions_furniture_id"),
        CheckConstraint("char_length(input_signature) = 64", name="input_signature_length"),
        CheckConstraint(
            "furniture_type IN ('chair', 'dining_table', 'bookshelf')",
            name="furniture_type_allowed",
        ),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="confidence_range",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    furniture_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("furniture.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    input_signature: Mapped[str] = mapped_column(String(64), nullable=False)
    furniture_type: Mapped[FurnitureType] = mapped_column(
        SAEnum(
            FurnitureType,
            name="reconstruction_furniture_type_values",
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            length=32,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
    )
    provider_name: Mapped[str] = mapped_column(String(100), nullable=False)
    provider_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    warnings: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )

    furniture: Mapped["Furniture"] = relationship(back_populates="reconstruction")
    parts: Mapped[list["FurnitureReconstructionPart"]] = relationship(
        back_populates="reconstruction",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="FurnitureReconstructionPart.sort_order",
    )
    plans: Mapped[list["FurniturePlan"]] = relationship(
        back_populates="source_reconstruction",
        passive_deletes=True,
    )
