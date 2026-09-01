"""Dated per-hour price history for a labor rate."""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.labor_rate import LaborRate


class LaborRatePrice(TimestampMixin, Base):
    """One effective-dated hourly value with no currency semantics."""

    __tablename__ = "labor_rate_prices"
    __table_args__ = (
        CheckConstraint("rate_per_hour >= 0", name="rate_nonnegative"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    labor_rate_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("labor_rates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rate_per_hour: Mapped[Decimal] = mapped_column(
        Numeric(18, 6),
        nullable=False,
    )
    effective_date: Mapped[date] = mapped_column(nullable=False, index=True)

    labor_rate: Mapped["LaborRate"] = relationship(back_populates="prices")
