"""Admin-managed labor rate catalog item."""

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, String, UniqueConstraint, Uuid, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.labor_rate_price import LaborRatePrice


class LaborRate(TimestampMixin, Base):
    """A named, independently managed hourly labor rate."""

    __tablename__ = "labor_rates"
    __table_args__ = (
        UniqueConstraint("rate_name", name="uq_labor_rates_rate_name"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    rate_name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
        index=True,
    )

    prices: Mapped[list["LaborRatePrice"]] = relationship(
        back_populates="labor_rate",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by=(
            "(LaborRatePrice.effective_date.desc(), "
            "LaborRatePrice.created_at.desc(), LaborRatePrice.id.desc())"
        ),
    )
