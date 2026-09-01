"""Read-only hardware cost calculation response schema."""

from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.enums import FurnitureType, MaterialUnit
from app.schemas.hardware_quantity import HardwareConnectionQuantityRead


class HardwareCostRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    plan_id: UUID
    furniture_id: UUID
    revision: int
    furniture_type: FurnitureType
    item_code: Literal["wood_screw"]
    item_name: Literal["Wood screw"]
    category: Literal["hardware"]
    rule_name: Literal["WUE v1 wood-screw connection rule"]
    screws_per_connection: int
    connections: list[HardwareConnectionQuantityRead]
    total_connections: int
    material_id: UUID
    material_name: str
    price_id: UUID
    price_per_piece: Decimal
    price_unit: MaterialUnit
    price_effective_date: date
    quantity: int
    total_cost: Decimal
