"""Pure composition of wood, hardware, and labor costs."""

from dataclasses import dataclass
from decimal import Decimal, localcontext

from app.models.furniture_plan import FurniturePlan
from app.models.labor_rate import LaborRate
from app.models.labor_rate_price import LaborRatePrice
from app.models.material import Material
from app.models.material_price import MaterialPrice
from app.services.hardware_cost import HardwareCost, calculate_hardware_cost
from app.services.labor_cost import LaborCost, calculate_labor_cost
from app.services.material_cost import MaterialCost, calculate_material_cost

CALCULATION_PRECISION = 40


@dataclass(frozen=True, slots=True)
class CompleteCost:
    material: MaterialCost
    hardware: HardwareCost
    labor: LaborCost
    total_cost: Decimal


def calculate_complete_cost(
    plan: FurniturePlan,
    wood_material: Material,
    wood_price: MaterialPrice | None,
    hardware_material: Material,
    hardware_price: MaterialPrice | None,
    labor_rate: LaborRate,
    labor_rate_price: LaborRatePrice | None,
) -> CompleteCost:
    """Combine exactly three approved cost domains with no overhead."""
    material = calculate_material_cost(plan, wood_material, wood_price)
    hardware = calculate_hardware_cost(
        plan,
        hardware_material,
        hardware_price,
    )
    labor = calculate_labor_cost(plan, labor_rate, labor_rate_price)
    with localcontext() as context:
        context.prec = CALCULATION_PRECISION
        total_cost = material.total_cost + hardware.total_cost + labor.total_cost
    return CompleteCost(
        material=material,
        hardware=hardware,
        labor=labor,
        total_cost=total_cost,
    )
