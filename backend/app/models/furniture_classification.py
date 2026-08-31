"""Persisted furniture classification result."""

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Enum as SAEnum,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import FurnitureType
from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.furniture import Furniture


class FurnitureClassification(TimestampMixin, Base):
    """The latest classifier result for one furniture item."""

    __tablename__ = "furniture_classifications"
    __table_args__ = (
        UniqueConstraint(
            "furniture_id",
            name="uq_furniture_classifications_furniture_id",
        ),
        CheckConstraint(
            "predicted_type IN ('chair', 'dining_table', 'bookshelf')",
            name="predicted_type_allowed",
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
    )
    predicted_type: Mapped[FurnitureType] = mapped_column(
        SAEnum(
            FurnitureType,
            name="classification_furniture_type_values",
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            length=32,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
    )
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    classifier_name: Mapped[str] = mapped_column(String(100), nullable=False)
    classifier_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    input_signature: Mapped[str] = mapped_column(String(64), nullable=False)

    furniture: Mapped["Furniture"] = relationship(back_populates="classification")
