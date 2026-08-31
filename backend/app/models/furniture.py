"""Furniture ORM model."""

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Enum as SAEnum, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import FurnitureType
from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.furniture_image import FurnitureImage
    from app.models.project import Project


class Furniture(TimestampMixin, Base):
    """A furniture design belonging to exactly one project."""

    __tablename__ = "furniture"
    __table_args__ = (
        CheckConstraint(
            "furniture_type IN ('chair', 'dining_table', 'bookshelf')",
            name="furniture_type_allowed",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    furniture_type: Mapped[FurnitureType] = mapped_column(
        SAEnum(
            FurnitureType,
            name="furniture_type_values",
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            length=32,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
        index=True,
    )

    project: Mapped["Project"] = relationship(back_populates="furniture_items")
    images: Mapped[list["FurnitureImage"]] = relationship(
        back_populates="furniture",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
