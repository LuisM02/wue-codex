"""Versioned parametric 2D furniture plan."""

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import FurnitureType, PlanStatus
from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.furniture import Furniture
    from app.models.furniture_component import FurnitureComponent


class FurniturePlan(TimestampMixin, Base):
    """One immutable-by-revision design container for a furniture item."""

    __tablename__ = "furniture_plans"
    __table_args__ = (
        UniqueConstraint(
            "furniture_id",
            "revision",
            name="uq_furniture_plans_furniture_revision",
        ),
        CheckConstraint("revision > 0", name="revision_positive"),
        CheckConstraint(
            "status IN ('draft', 'finalized')",
            name="status_allowed",
        ),
        CheckConstraint(
            "furniture_type IN ('chair', 'dining_table', 'bookshelf')",
            name="furniture_type_allowed",
        ),
        Index(
            "uq_furniture_plans_one_draft_per_furniture",
            "furniture_id",
            unique=True,
            postgresql_where=text("status = 'draft'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    furniture_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("furniture.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[PlanStatus] = mapped_column(
        SAEnum(
            PlanStatus,
            name="plan_status_values",
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            length=16,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
        default=PlanStatus.DRAFT,
    )
    furniture_type: Mapped[FurnitureType] = mapped_column(
        SAEnum(
            FurnitureType,
            name="plan_furniture_type_values",
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            length=32,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
    )

    furniture: Mapped["Furniture"] = relationship(back_populates="plans")
    components: Mapped[list["FurnitureComponent"]] = relationship(
        back_populates="plan",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by=(
            "(FurnitureComponent.sort_order, FurnitureComponent.created_at, "
            "FurnitureComponent.id)"
        ),
    )
