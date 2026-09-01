"""Complete estimate and immutable quotation API schemas."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.enums import FurnitureType, MaterialUnit
from app.schemas.hardware_cost import HardwareCostRead
from app.schemas.labor_cost import LaborCostRead
from app.schemas.material_cost import MaterialCostRead


class CostSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    material_id: UUID
    hardware_material_id: UUID
    labor_rate_id: UUID


class CompleteCostRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    material: MaterialCostRead
    hardware: HardwareCostRead
    labor: LaborCostRead
    total_cost: Decimal


class QuotationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    quotation_number: str
    project_id: UUID
    furniture_id: UUID
    plan_id: UUID
    plan_revision: int
    furniture_type: FurnitureType
    wood_material_id: UUID
    wood_material_name: str
    wood_price_id: UUID
    wood_price_per_unit: Decimal
    wood_price_unit: MaterialUnit
    wood_price_effective_date: date
    wood_quantity: Decimal
    wood_material_cost: Decimal
    hardware_material_id: UUID
    hardware_material_name: str
    hardware_price_id: UUID
    hardware_price_per_piece: Decimal
    hardware_price_effective_date: date
    hardware_quantity: int
    hardware_cost: Decimal
    labor_rate_id: UUID
    labor_rate_name: str
    labor_rate_price_id: UUID
    labor_rate_per_hour: Decimal
    labor_rate_effective_date: date
    labor_hours: Decimal
    labor_cost: Decimal
    total_cost: Decimal
    created_at: datetime
    updated_at: datetime
