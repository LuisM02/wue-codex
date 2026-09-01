"""Pure Decimal wood-screw cost calculation."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, localcontext
from typing import Literal
from uuid import UUID

from app.core.enums import FurnitureType, MaterialType, MaterialUnit
from app.models.material import Material
from app.models.material_price import MaterialPrice
from app.services.hardware_quantity import (
    HardwareConnectionQuantity,
    HardwarePlan,
    calculate_hardware_quantity,
)

CALCULATION_PRECISION = 40
WOOD_SCREW_NAME = "wood screw"


class HardwareMaterialRequiredError(RuntimeError):
    """Raised when hardware costing receives a non-hardware material."""


class ActiveHardwareRequiredError(RuntimeError):
    """Raised when a disabled hardware item is selected for costing."""


class PieceUnitRequiredError(RuntimeError):
    """Raised when selected hardware is not administered per piece."""


class WoodScrewNameRequiredError(RuntimeError):
    """Raised when selected hardware does not represent wood screws."""


class HardwarePriceRequiredError(RuntimeError):
    """Raised when selected hardware has no dated price history."""


class HardwarePriceMismatchError(RuntimeError):
    """Raised when price history does not match selected hardware."""


@dataclass(frozen=True, slots=True)
class HardwareCost:
    plan_id: UUID
    furniture_id: UUID
    revision: int
    furniture_type: FurnitureType
    item_code: Literal["wood_screw"]
    item_name: Literal["Wood screw"]
    category: Literal["hardware"]
    rule_name: Literal["WUE v1 wood-screw connection rule"]
    screws_per_connection: int
    connections: tuple[HardwareConnectionQuantity, ...]
    total_connections: int
    material_id: UUID
    material_name: str
    price_id: UUID
    price_per_piece: Decimal
    price_unit: MaterialUnit
    price_effective_date: date
    quantity: int
    total_cost: Decimal


def _validate_selection(material: Material, price: MaterialPrice) -> None:
    if not material.is_active:
        raise ActiveHardwareRequiredError(
            "Hardware cost calculation requires an active material"
        )
    if material.material_type != MaterialType.HARDWARE:
        raise HardwareMaterialRequiredError(
            "Hardware cost calculation requires a hardware material"
        )
    if material.unit != MaterialUnit.PIECE:
        raise PieceUnitRequiredError(
            "Hardware cost calculation requires unit piece"
        )
    if material.material_name.strip().casefold() != WOOD_SCREW_NAME:
        raise WoodScrewNameRequiredError(
            "Hardware cost calculation requires material name Wood screw"
        )
    if (
        price.material_id != material.id
        or price.unit != material.unit
        or price.unit != MaterialUnit.PIECE
    ):
        raise HardwarePriceMismatchError(
            "Latest price does not match the selected hardware"
        )


def calculate_hardware_cost(
    plan: HardwarePlan,
    material: Material,
    price: MaterialPrice | None,
) -> HardwareCost:
    """Price the live WUE v1 screw quantity without persisting an estimate."""
    if price is None:
        raise HardwarePriceRequiredError(
            "Selected hardware has no price history"
        )
    _validate_selection(material, price)
    quantity = calculate_hardware_quantity(plan)
    with localcontext() as context:
        context.prec = CALCULATION_PRECISION
        total_cost = Decimal(quantity.total_quantity) * price.price_per_unit
    return HardwareCost(
        plan_id=quantity.plan_id,
        furniture_id=quantity.furniture_id,
        revision=quantity.revision,
        furniture_type=quantity.furniture_type,
        item_code=quantity.item_code,
        item_name=quantity.item_name,
        category=quantity.category,
        rule_name=quantity.rule_name,
        screws_per_connection=quantity.screws_per_connection,
        connections=quantity.connections,
        total_connections=quantity.total_connections,
        material_id=material.id,
        material_name=material.material_name,
        price_id=price.id,
        price_per_piece=price.price_per_unit,
        price_unit=price.unit,
        price_effective_date=price.effective_date,
        quantity=quantity.total_quantity,
        total_cost=total_cost,
    )
