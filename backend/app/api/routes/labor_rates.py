"""Administrative labor-rate and dated-price endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.models.labor_rate import LaborRate
from app.models.labor_rate_price import LaborRatePrice
from app.schemas.labor_rates import (
    LaborRateCreate,
    LaborRatePriceCreate,
    LaborRatePriceRead,
    LaborRatePriceUpdate,
    LaborRateRead,
    LaborRateUpdate,
)
from app.services import labor_rates as labor_rate_service

rates_router = APIRouter(prefix="/admin/labor-rates", tags=["admin-labor-rates"])
prices_router = APIRouter(
    prefix="/admin/labor-rate-prices",
    tags=["admin-labor-rates"],
)
SessionDependency = Annotated[Session, Depends(get_db_session)]


def require_rate(session: Session, labor_rate_id: UUID) -> LaborRate:
    labor_rate = labor_rate_service.get_labor_rate(session, labor_rate_id)
    if labor_rate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Labor rate not found",
        )
    return labor_rate


def require_price(session: Session, price_id: UUID) -> LaborRatePrice:
    price = labor_rate_service.get_price(session, price_id)
    if price is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Labor rate price not found",
        )
    return price


@rates_router.post("", response_model=LaborRateRead, status_code=status.HTTP_201_CREATED)
def create_labor_rate(
    payload: LaborRateCreate,
    session: SessionDependency,
) -> LaborRateRead:
    try:
        return labor_rate_service.create_labor_rate(session, payload)
    except labor_rate_service.LaborRateNameConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@rates_router.get("", response_model=list[LaborRateRead])
def list_labor_rates(
    session: SessionDependency,
    is_active: bool | None = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[LaborRateRead]:
    return labor_rate_service.list_labor_rates(
        session,
        is_active=is_active,
        offset=offset,
        limit=limit,
    )


@rates_router.get("/{labor_rate_id}", response_model=LaborRateRead)
def get_labor_rate(
    labor_rate_id: UUID,
    session: SessionDependency,
) -> LaborRateRead:
    return require_rate(session, labor_rate_id)


@rates_router.patch("/{labor_rate_id}", response_model=LaborRateRead)
def update_labor_rate(
    labor_rate_id: UUID,
    payload: LaborRateUpdate,
    session: SessionDependency,
) -> LaborRateRead:
    labor_rate = require_rate(session, labor_rate_id)
    try:
        return labor_rate_service.update_labor_rate(session, labor_rate, payload)
    except labor_rate_service.LaborRateNameConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@rates_router.delete("/{labor_rate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_labor_rate(
    labor_rate_id: UUID,
    session: SessionDependency,
) -> Response:
    labor_rate_service.delete_labor_rate(
        session,
        require_rate(session, labor_rate_id),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@rates_router.post(
    "/{labor_rate_id}/prices",
    response_model=LaborRatePriceRead,
    status_code=status.HTTP_201_CREATED,
)
def create_price(
    labor_rate_id: UUID,
    payload: LaborRatePriceCreate,
    session: SessionDependency,
) -> LaborRatePriceRead:
    return labor_rate_service.create_price(
        session,
        require_rate(session, labor_rate_id),
        payload,
    )


@rates_router.get(
    "/{labor_rate_id}/prices",
    response_model=list[LaborRatePriceRead],
)
def list_prices(
    labor_rate_id: UUID,
    session: SessionDependency,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[LaborRatePriceRead]:
    require_rate(session, labor_rate_id)
    return labor_rate_service.list_prices(
        session,
        labor_rate_id,
        offset=offset,
        limit=limit,
    )


@prices_router.get("/{price_id}", response_model=LaborRatePriceRead)
def get_price(price_id: UUID, session: SessionDependency) -> LaborRatePriceRead:
    return require_price(session, price_id)


@prices_router.patch("/{price_id}", response_model=LaborRatePriceRead)
def update_price(
    price_id: UUID,
    payload: LaborRatePriceUpdate,
    session: SessionDependency,
) -> LaborRatePriceRead:
    return labor_rate_service.update_price(
        session,
        require_price(session, price_id),
        payload,
    )


@prices_router.delete("/{price_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_price(price_id: UUID, session: SessionDependency) -> Response:
    labor_rate_service.delete_price(session, require_price(session, price_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
