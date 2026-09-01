"""Administrative labor-rate catalog and dated-price persistence."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.labor_rate import LaborRate
from app.models.labor_rate_price import LaborRatePrice
from app.schemas.labor_rates import (
    LaborRateCreate,
    LaborRatePriceCreate,
    LaborRatePriceUpdate,
    LaborRateUpdate,
)
from app.services._persistence import commit, commit_and_refresh


class LaborRateNameConflictError(RuntimeError):
    """Raised when an exact labor-rate name already exists."""


def _commit_rate(session: Session, labor_rate: LaborRate) -> None:
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
        if constraint == "uq_labor_rates_rate_name":
            raise LaborRateNameConflictError(
                "A labor rate with this name already exists"
            ) from exc
        raise
    session.refresh(labor_rate)


def create_labor_rate(
    session: Session,
    payload: LaborRateCreate,
) -> LaborRate:
    labor_rate = LaborRate(**payload.model_dump())
    session.add(labor_rate)
    _commit_rate(session, labor_rate)
    return labor_rate


def list_labor_rates(
    session: Session,
    *,
    is_active: bool | None,
    offset: int,
    limit: int,
) -> list[LaborRate]:
    statement = select(LaborRate)
    if is_active is not None:
        statement = statement.where(LaborRate.is_active == is_active)
    statement = statement.order_by(
        LaborRate.rate_name.asc(),
        LaborRate.id.asc(),
    ).offset(offset).limit(limit)
    return list(session.scalars(statement).all())


def get_labor_rate(session: Session, labor_rate_id: UUID) -> LaborRate | None:
    return session.get(LaborRate, labor_rate_id)


def update_labor_rate(
    session: Session,
    labor_rate: LaborRate,
    payload: LaborRateUpdate,
) -> LaborRate:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(labor_rate, field, value)
    _commit_rate(session, labor_rate)
    return labor_rate


def delete_labor_rate(session: Session, labor_rate: LaborRate) -> None:
    session.delete(labor_rate)
    commit(session)


def create_price(
    session: Session,
    labor_rate: LaborRate,
    payload: LaborRatePriceCreate,
) -> LaborRatePrice:
    price = LaborRatePrice(
        labor_rate_id=labor_rate.id,
        created_at=datetime.now(timezone.utc),
        **payload.model_dump(),
    )
    session.add(price)
    commit_and_refresh(session, price)
    return price


def list_prices(
    session: Session,
    labor_rate_id: UUID,
    *,
    offset: int,
    limit: int,
) -> list[LaborRatePrice]:
    statement = (
        select(LaborRatePrice)
        .where(LaborRatePrice.labor_rate_id == labor_rate_id)
        .order_by(
            LaborRatePrice.effective_date.desc(),
            LaborRatePrice.created_at.desc(),
            LaborRatePrice.id.desc(),
        )
        .offset(offset)
        .limit(limit)
    )
    return list(session.scalars(statement).all())


def get_latest_price(
    session: Session,
    labor_rate_id: UUID,
) -> LaborRatePrice | None:
    """Select latest by effective and creation dates, with no today filter."""
    statement = (
        select(LaborRatePrice)
        .where(LaborRatePrice.labor_rate_id == labor_rate_id)
        .order_by(
            LaborRatePrice.effective_date.desc(),
            LaborRatePrice.created_at.desc(),
            LaborRatePrice.id.desc(),
        )
        .limit(1)
    )
    return session.scalar(statement)


def get_price(session: Session, price_id: UUID) -> LaborRatePrice | None:
    return session.get(LaborRatePrice, price_id)


def update_price(
    session: Session,
    price: LaborRatePrice,
    payload: LaborRatePriceUpdate,
) -> LaborRatePrice:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(price, field, value)
    commit_and_refresh(session, price)
    return price


def delete_price(session: Session, price: LaborRatePrice) -> None:
    session.delete(price)
    commit(session)
