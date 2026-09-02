"""Canonical dimension conversion, persistence, precedence, and locking."""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from types import MappingProxyType
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import DimensionSource, DimensionUnit
from app.models.furniture import Furniture
from app.models.furniture_dimensions import FurnitureDimensions
from app.schemas.dimensions import FurnitureDimensionsWrite
from app.services._persistence import commit, commit_and_refresh
from app.services.reconstruction_state import invalidate_reconstruction

CANONICAL_QUANTUM_MM = Decimal("0.0001")
MAX_CANONICAL_MM = Decimal("9999999999.9999")
UNIT_TO_MM = MappingProxyType(
    {
        DimensionUnit.MILLIMETER: Decimal("1"),
        DimensionUnit.CENTIMETER: Decimal("10"),
        DimensionUnit.METER: Decimal("1000"),
        DimensionUnit.INCH: Decimal("25.4"),
    }
)


class DimensionRangeError(ValueError):
    """Raised when a converted value cannot fit canonical storage."""


class DimensionsLockedError(RuntimeError):
    """Raised when finalized geometry prerequisites forbid dimension mutation."""


class ManualDimensionsConflictError(RuntimeError):
    """Raised when an AI estimate attempts to replace trusted manual input."""


class DimensionsRequiredError(RuntimeError):
    """Raised when 2D generation is attempted without dimensions."""


@dataclass(frozen=True, slots=True)
class CanonicalDimensions:
    width_mm: Decimal
    height_mm: Decimal
    depth_mm: Decimal


def convert_to_mm(value: Decimal, unit: DimensionUnit) -> Decimal:
    converted = (value * UNIT_TO_MM[unit]).quantize(
        CANONICAL_QUANTUM_MM,
        rounding=ROUND_HALF_UP,
    )
    if converted <= 0 or converted > MAX_CANONICAL_MM:
        raise DimensionRangeError(
            f"Converted dimension must be between {CANONICAL_QUANTUM_MM} "
            f"and {MAX_CANONICAL_MM} millimeters"
        )
    return converted


def convert_from_mm(value_mm: Decimal, unit: DimensionUnit) -> Decimal:
    """Convert canonical millimeters without applying display rounding."""
    return value_mm / UNIT_TO_MM[unit]


def canonicalize(payload: FurnitureDimensionsWrite) -> CanonicalDimensions:
    """Map width=X, height=Y, and depth=Z into canonical millimeters."""
    return CanonicalDimensions(
        width_mm=convert_to_mm(payload.width, payload.unit),
        height_mm=convert_to_mm(payload.height, payload.unit),
        depth_mm=convert_to_mm(payload.depth, payload.unit),
    )


def get_dimensions(
    session: Session,
    furniture_id: UUID,
    *,
    for_update: bool = False,
) -> FurnitureDimensions | None:
    statement = select(FurnitureDimensions).where(
        FurnitureDimensions.furniture_id == furniture_id
    )
    if for_update:
        statement = statement.with_for_update()
    return session.scalar(statement)


def set_dimensions(
    session: Session,
    furniture: Furniture,
    payload: FurnitureDimensionsWrite,
) -> tuple[FurnitureDimensions, bool]:
    dimensions = get_dimensions(session, furniture.id)
    created = dimensions is None
    if dimensions is not None and dimensions.is_locked:
        raise DimensionsLockedError(
            "Overall dimensions are locked because a 2D plan has been generated"
        )
    if (
        dimensions is not None
        and dimensions.source == DimensionSource.MANUAL
        and payload.source == DimensionSource.AI_ESTIMATE
    ):
        raise ManualDimensionsConflictError(
            "AI-estimated dimensions cannot replace trusted manual dimensions"
        )

    canonical = canonicalize(payload)
    invalidate_reconstruction(session, furniture.id)
    if dimensions is None:
        dimensions = FurnitureDimensions(furniture_id=furniture.id)
        session.add(dimensions)
    dimensions.width_mm = canonical.width_mm
    dimensions.height_mm = canonical.height_mm
    dimensions.depth_mm = canonical.depth_mm
    dimensions.unit = payload.unit
    dimensions.source = payload.source
    commit_and_refresh(session, dimensions)
    return dimensions, created


def delete_dimensions(session: Session, dimensions: FurnitureDimensions) -> None:
    if dimensions.is_locked:
        raise DimensionsLockedError(
            "Overall dimensions are locked because a 2D plan has been generated"
        )
    invalidate_reconstruction(session, dimensions.furniture_id)
    session.delete(dimensions)
    commit(session)


def lock_dimensions_for_plan(
    session: Session,
    furniture_id: UUID,
) -> FurnitureDimensions:
    """Lock dimensions inside the caller's future 2D-plan transaction."""
    dimensions = get_dimensions(session, furniture_id, for_update=True)
    if dimensions is None:
        raise DimensionsRequiredError(
            "Overall dimensions are required before generating a 2D plan"
        )
    if not dimensions.is_locked:
        dimensions.is_locked = True
        dimensions.locked_at = datetime.now(timezone.utc)
        session.flush()
    return dimensions
