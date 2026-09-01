"""Administrative material catalog and price-history persistence."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.enums import MaterialType, MaterialUnit
from app.models.material import Material
from app.models.material_price import MaterialPrice
from app.schemas.materials import (
    MaterialCreate,
    MaterialPriceCreate,
    MaterialPriceUpdate,
    MaterialUpdate,
    is_compatible_unit,
)
from app.services._persistence import commit, commit_and_refresh


class InvalidMaterialUnitError(ValueError):
    """Raised when a material category is paired with an unsupported unit."""


class MaterialNameConflictError(RuntimeError):
    """Raised when the exact administrative material name already exists."""


class MaterialPriceHistoryConflictError(RuntimeError):
    """Raised when a unit mutation would reinterpret existing price history."""


def _ensure_compatible_unit(
    material_type: MaterialType,
    unit: MaterialUnit,
) -> None:
    if not is_compatible_unit(material_type, unit):
        raise InvalidMaterialUnitError("Material type and unit are incompatible")


def _commit_material(session: Session, material: Material) -> None:
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
        if constraint == "uq_materials_material_name":
            raise MaterialNameConflictError(
                "A material with this name already exists"
            ) from exc
        raise
    session.refresh(material)


def create_material(session: Session, payload: MaterialCreate) -> Material:
    _ensure_compatible_unit(payload.material_type, payload.unit)
    material = Material(**payload.model_dump())
    session.add(material)
    _commit_material(session, material)
    return material


def list_materials(
    session: Session,
    *,
    material_type: MaterialType | None,
    is_active: bool | None,
    offset: int,
    limit: int,
) -> list[Material]:
    statement = select(Material)
    if material_type is not None:
        statement = statement.where(Material.material_type == material_type)
    if is_active is not None:
        statement = statement.where(Material.is_active == is_active)
    statement = statement.order_by(
        Material.material_name.asc(),
        Material.id.asc(),
    ).offset(offset).limit(limit)
    return list(session.scalars(statement).all())


def get_material(session: Session, material_id: UUID) -> Material | None:
    return session.get(Material, material_id)


def _material_has_prices(session: Session, material_id: UUID) -> bool:
    statement = select(func.count()).select_from(MaterialPrice).where(
        MaterialPrice.material_id == material_id
    )
    return bool(session.scalar(statement))


def update_material(
    session: Session,
    material: Material,
    payload: MaterialUpdate,
) -> Material:
    updates = payload.model_dump(exclude_unset=True)
    updated_type = updates.get("material_type", material.material_type)
    updated_unit = updates.get("unit", material.unit)
    _ensure_compatible_unit(updated_type, updated_unit)
    changes_unit_semantics = (
        updated_type != material.material_type or updated_unit != material.unit
    )
    if changes_unit_semantics and _material_has_prices(session, material.id):
        raise MaterialPriceHistoryConflictError(
            "Material type and unit cannot change after price history exists"
        )
    for field, value in updates.items():
        setattr(material, field, value)
    _commit_material(session, material)
    return material


def delete_material(session: Session, material: Material) -> None:
    session.delete(material)
    commit(session)


def create_price(
    session: Session,
    material: Material,
    payload: MaterialPriceCreate,
) -> MaterialPrice:
    price = MaterialPrice(
        material_id=material.id,
        unit=material.unit,
        created_at=datetime.now(timezone.utc),
        **payload.model_dump(),
    )
    session.add(price)
    commit_and_refresh(session, price)
    return price


def list_prices(
    session: Session,
    material_id: UUID,
    *,
    offset: int,
    limit: int,
) -> list[MaterialPrice]:
    statement = (
        select(MaterialPrice)
        .where(MaterialPrice.material_id == material_id)
        .order_by(
            MaterialPrice.effective_date.desc(),
            MaterialPrice.created_at.desc(),
            MaterialPrice.id.desc(),
        )
        .offset(offset)
        .limit(limit)
    )
    return list(session.scalars(statement).all())


def get_price(session: Session, price_id: UUID) -> MaterialPrice | None:
    return session.get(MaterialPrice, price_id)


def update_price(
    session: Session,
    price: MaterialPrice,
    payload: MaterialPriceUpdate,
) -> MaterialPrice:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(price, field, value)
    commit_and_refresh(session, price)
    return price


def delete_price(session: Session, price: MaterialPrice) -> None:
    session.delete(price)
    commit(session)
