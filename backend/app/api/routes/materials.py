"""Administrative material catalog and price-history endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.enums import MaterialType
from app.db.session import get_db_session
from app.models.material import Material
from app.models.material_price import MaterialPrice
from app.schemas.materials import (
    MaterialCreate,
    MaterialPriceCreate,
    MaterialPriceRead,
    MaterialPriceUpdate,
    MaterialRead,
    MaterialUpdate,
)
from app.services import materials as material_service

materials_router = APIRouter(prefix="/admin/materials", tags=["admin-materials"])
prices_router = APIRouter(
    prefix="/admin/material-prices",
    tags=["admin-materials"],
)
SessionDependency = Annotated[Session, Depends(get_db_session)]


def require_material(session: Session, material_id: UUID) -> Material:
    material = material_service.get_material(session, material_id)
    if material is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")
    return material


def require_price(session: Session, price_id: UUID) -> MaterialPrice:
    price = material_service.get_price(session, price_id)
    if price is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Material price not found",
        )
    return price


@materials_router.post("", response_model=MaterialRead, status_code=status.HTTP_201_CREATED)
def create_material(
    payload: MaterialCreate,
    session: SessionDependency,
) -> MaterialRead:
    try:
        return material_service.create_material(session, payload)
    except material_service.MaterialNameConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@materials_router.get("", response_model=list[MaterialRead])
def list_materials(
    session: SessionDependency,
    material_type: MaterialType | None = None,
    is_active: bool | None = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[MaterialRead]:
    return material_service.list_materials(
        session,
        material_type=material_type,
        is_active=is_active,
        offset=offset,
        limit=limit,
    )


@materials_router.get("/{material_id}", response_model=MaterialRead)
def get_material(material_id: UUID, session: SessionDependency) -> MaterialRead:
    return require_material(session, material_id)


@materials_router.patch("/{material_id}", response_model=MaterialRead)
def update_material(
    material_id: UUID,
    payload: MaterialUpdate,
    session: SessionDependency,
) -> MaterialRead:
    material = require_material(session, material_id)
    try:
        return material_service.update_material(session, material, payload)
    except (
        material_service.InvalidMaterialUnitError,
        material_service.MaterialPriceHistoryConflictError,
        material_service.MaterialNameConflictError,
    ) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@materials_router.delete("/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_material(
    material_id: UUID,
    session: SessionDependency,
) -> Response:
    material = require_material(session, material_id)
    material_service.delete_material(session, material)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@materials_router.post(
    "/{material_id}/prices",
    response_model=MaterialPriceRead,
    status_code=status.HTTP_201_CREATED,
)
def create_price(
    material_id: UUID,
    payload: MaterialPriceCreate,
    session: SessionDependency,
) -> MaterialPriceRead:
    material = require_material(session, material_id)
    return material_service.create_price(session, material, payload)


@materials_router.get(
    "/{material_id}/prices",
    response_model=list[MaterialPriceRead],
)
def list_prices(
    material_id: UUID,
    session: SessionDependency,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[MaterialPriceRead]:
    require_material(session, material_id)
    return material_service.list_prices(
        session,
        material_id,
        offset=offset,
        limit=limit,
    )


@prices_router.get("/{price_id}", response_model=MaterialPriceRead)
def get_price(price_id: UUID, session: SessionDependency) -> MaterialPriceRead:
    return require_price(session, price_id)


@prices_router.patch("/{price_id}", response_model=MaterialPriceRead)
def update_price(
    price_id: UUID,
    payload: MaterialPriceUpdate,
    session: SessionDependency,
) -> MaterialPriceRead:
    price = require_price(session, price_id)
    return material_service.update_price(session, price, payload)


@prices_router.delete("/{price_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_price(price_id: UUID, session: SessionDependency) -> Response:
    price = require_price(session, price_id)
    material_service.delete_price(session, price)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
