"""Pure Decimal material cost conversion and calculation."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, localcontext
from types import MappingProxyType
from uuid import UUID

from app.core.enums import ComponentType, FurnitureType, MaterialType, MaterialUnit
from app.models.furniture_plan import FurniturePlan
from app.models.material import Material
from app.models.material_price import MaterialPrice
from app.services.material_quantity import calculate_material_quantity

BOARD_FOOT_IN_MM3 = Decimal("2359737.216")
CALCULATION_PRECISION = 40
VOLUME_UNIT_DIVISORS_MM3 = MappingProxyType(
    {
        MaterialUnit.CUBIC_MILLIMETER: Decimal("1"),
        MaterialUnit.CUBIC_CENTIMETER: Decimal("1000"),
        MaterialUnit.CUBIC_METER: Decimal("1000000000"),
        MaterialUnit.BOARD_FOOT: BOARD_FOOT_IN_MM3,
    }
)


class WoodMaterialRequiredError(RuntimeError):
    """Raised when volumetric wood costing receives a non-wood material."""


class ActiveMaterialRequiredError(RuntimeError):
    """Raised when a disabled catalog item is selected for costing."""


class MaterialPriceRequiredError(RuntimeError):
    """Raised when a selected material has no dated price history."""


class MaterialPriceUnitMismatchError(RuntimeError):
    """Raised when price history no longer matches its material unit."""


class UnsupportedVolumeUnitError(ValueError):
    """Raised when a non-volumetric price unit is used for wood volume."""


@dataclass(frozen=True, slots=True)
class ComponentMaterialCost:
    source_component_id: UUID
    component_name: str
    component_type: ComponentType
    total_volume_mm3: Decimal
    quantity_in_price_unit: Decimal
    cost: Decimal
    sort_order: int


@dataclass(frozen=True, slots=True)
class MaterialCost:
    plan_id: UUID
    furniture_id: UUID
    revision: int
    furniture_type: FurnitureType
    material_id: UUID
    material_name: str
    price_id: UUID
    price_per_unit: Decimal
    price_unit: MaterialUnit
    price_effective_date: date
    total_volume_mm3: Decimal
    total_quantity_in_price_unit: Decimal
    components: tuple[ComponentMaterialCost, ...]
    total_cost: Decimal


def convert_volume_from_mm3(
    volume_mm3: Decimal,
    unit: MaterialUnit,
) -> Decimal:
    """Convert canonical volume with a fixed high-precision Decimal context."""
    divisor = VOLUME_UNIT_DIVISORS_MM3.get(unit)
    if divisor is None:
        raise UnsupportedVolumeUnitError(
            f"Material unit {unit.value} is not a supported volume price unit"
        )
    with localcontext() as context:
        context.prec = CALCULATION_PRECISION
        return volume_mm3 / divisor


def _validate_selection(material: Material, price: MaterialPrice) -> None:
    if material.material_type != MaterialType.WOOD:
        raise WoodMaterialRequiredError(
            "Material cost calculation requires a wood material"
        )
    if not material.is_active:
        raise ActiveMaterialRequiredError(
            "Material cost calculation requires an active material"
        )
    if price.material_id != material.id or price.unit != material.unit:
        raise MaterialPriceUnitMismatchError(
            "Latest price unit does not match the selected material"
        )
    if material.unit not in VOLUME_UNIT_DIVISORS_MM3:
        raise UnsupportedVolumeUnitError(
            f"Material unit {material.unit.value} is not a supported volume price unit"
        )


def calculate_material_cost(
    plan: FurniturePlan,
    material: Material,
    price: MaterialPrice | None,
) -> MaterialCost:
    """Calculate a component breakdown using finalized live geometry."""
    if price is None:
        raise MaterialPriceRequiredError(
            "Selected material has no price history"
        )
    _validate_selection(material, price)
    quantity = calculate_material_quantity(plan)
    components: list[ComponentMaterialCost] = []
    with localcontext() as context:
        context.prec = CALCULATION_PRECISION
        for item in quantity.components:
            converted_quantity = convert_volume_from_mm3(
                item.total_volume_mm3,
                material.unit,
            )
            components.append(
                ComponentMaterialCost(
                    source_component_id=item.source_component_id,
                    component_name=item.component_name,
                    component_type=item.component_type,
                    total_volume_mm3=item.total_volume_mm3,
                    quantity_in_price_unit=converted_quantity,
                    cost=converted_quantity * price.price_per_unit,
                    sort_order=item.sort_order,
                )
            )
        total_quantity = sum(
            (item.quantity_in_price_unit for item in components),
            start=Decimal("0"),
        )
        total_cost = sum(
            (item.cost for item in components),
            start=Decimal("0"),
        )
    return MaterialCost(
        plan_id=quantity.plan_id,
        furniture_id=quantity.furniture_id,
        revision=quantity.revision,
        furniture_type=quantity.furniture_type,
        material_id=material.id,
        material_name=material.material_name,
        price_id=price.id,
        price_per_unit=price.price_per_unit,
        price_unit=price.unit,
        price_effective_date=price.effective_date,
        total_volume_mm3=quantity.total_volume_mm3,
        total_quantity_in_price_unit=total_quantity,
        components=tuple(components),
        total_cost=total_cost,
    )
