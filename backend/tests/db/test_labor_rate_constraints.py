"""PostgreSQL constraints for separate labor rates and prices."""

from uuid import uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.labor_rate import LaborRate
from app.models.labor_rate_price import LaborRatePrice
from app.schemas.labor_rates import LaborRateCreate, LaborRatePriceCreate
from app.services.labor_rates import create_labor_rate, create_price

pytestmark = pytest.mark.integration


def test_postgresql_rejects_negative_hourly_rate(db_session: Session) -> None:
    labor_rate = create_labor_rate(
        db_session,
        LaborRateCreate(rate_name=f"Constraint {uuid4()}"),
    )

    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.execute(
                text(
                    """
                    INSERT INTO labor_rate_prices (
                        id, labor_rate_id, rate_per_hour, effective_date
                    ) VALUES (
                        :id, :labor_rate_id, :rate_per_hour, :effective_date
                    )
                    """
                ),
                {
                    "id": str(uuid4()),
                    "labor_rate_id": str(labor_rate.id),
                    "rate_per_hour": "-0.000001",
                    "effective_date": "2026-01-01",
                },
            )


def test_deleting_rate_cascades_to_price_history(db_session: Session) -> None:
    labor_rate = create_labor_rate(
        db_session,
        LaborRateCreate(rate_name=f"Cascade {uuid4()}"),
    )
    price = create_price(
        db_session,
        labor_rate,
        LaborRatePriceCreate(
            rate_per_hour="125.5",
            effective_date="2026-01-01",
        ),
    )
    price_id = price.id

    db_session.delete(labor_rate)
    db_session.commit()

    assert db_session.get(LaborRate, labor_rate.id) is None
    assert db_session.get(LaborRatePrice, price_id) is None
    assert db_session.scalar(
        select(func.count()).select_from(LaborRatePrice).where(
            LaborRatePrice.labor_rate_id == labor_rate.id
        )
    ) == 0
