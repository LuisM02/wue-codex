"""Read-only material cost calculation response schemas."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.enums import ComponentType, FurnitureType, MaterialUnit


class ComponentMaterialCostRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    source_component_id: UUID
    component_name: str
    component_type: ComponentType
    total_volume_mm3: Decimal
    quantity_in_price_unit: Decimal
    cost: Decimal
    sort_order: int


class MaterialCostRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

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
    components: list[ComponentMaterialCostRead]
    total_cost: Decimal
