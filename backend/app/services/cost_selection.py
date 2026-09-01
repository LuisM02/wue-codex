"""Central database selection boundary for complete cost calculations."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.furniture_plan import FurniturePlan
from app.services import hardware_cost, hardware_quantity
from app.services import labor_cost, labor_quantity, labor_rates
from app.services import material_cost, materials, reconstruction_3d
from app.services.complete_cost import CompleteCost, calculate_complete_cost


class SelectedCostResourceNotFoundError(LookupError):
    """Raised when a selected catalog resource does not exist."""


CALCULATION_STATE_ERRORS = (
    material_cost.WoodMaterialRequiredError,
    material_cost.ActiveMaterialRequiredError,
    material_cost.MaterialPriceRequiredError,
    material_cost.MaterialPriceUnitMismatchError,
    material_cost.UnsupportedVolumeUnitError,
    hardware_cost.HardwareMaterialRequiredError,
    hardware_cost.ActiveHardwareRequiredError,
    hardware_cost.PieceUnitRequiredError,
    hardware_cost.WoodScrewNameRequiredError,
    hardware_cost.HardwarePriceRequiredError,
    hardware_cost.HardwarePriceMismatchError,
    labor_cost.ActiveLaborRateRequiredError,
    labor_cost.LaborRatePriceRequiredError,
    labor_cost.LaborRatePriceMismatchError,
    reconstruction_3d.PlanNotFinalizedError,
    reconstruction_3d.ComponentDepthRequiredError,
    hardware_quantity.PlanNotFinalizedError,
    labor_quantity.PlanNotFinalizedError,
)


def calculate_selected_complete_cost(
    session: Session,
    plan: FurniturePlan,
    *,
    material_id: UUID,
    hardware_material_id: UUID,
    labor_rate_id: UUID,
) -> CompleteCost:
    """Resolve selected catalogs and calculate one live complete estimate."""
    wood_material = materials.get_material(session, material_id)
    if wood_material is None:
        raise SelectedCostResourceNotFoundError("Wood material not found")
    hardware_material = materials.get_material(session, hardware_material_id)
    if hardware_material is None:
        raise SelectedCostResourceNotFoundError("Hardware material not found")
    labor_rate = labor_rates.get_labor_rate(session, labor_rate_id)
    if labor_rate is None:
        raise SelectedCostResourceNotFoundError("Labor rate not found")

    return calculate_complete_cost(
        plan,
        wood_material,
        materials.get_latest_price(session, wood_material.id),
        hardware_material,
        materials.get_latest_price(session, hardware_material.id),
        labor_rate,
        labor_rates.get_latest_price(session, labor_rate.id),
    )
